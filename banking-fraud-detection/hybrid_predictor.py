# hybrid_predictor.py
"""
Clean, calibrated hybrid predictor for BAIDS.

Flow:
 - extract features from login_event (uses utils.feature_extractor_login.extract_features_from_login)
 - build numeric vector (order preserved)
 - scale with loaded scaler
 - get IsolationForest decision_function (normalized into anomaly score 0..1)
 - get Autoencoder reconstruction error (normalized wrt ae_threshold)
 - compute rule_score (0..100) from utils.rules.compute_rule_risk_score
 - combine into final_score using profile weights and return verdict + explanations

Notes:
 - Calibrate `ae_threshold` and IF mapping parameters (if_midpoint, if_steepness) on a held-out
   validation dataset for reliable numeric mapping.
 - This module intentionally has conservative defaults and safe fallbacks so API won't crash.
"""

import os
import json
import logging
from typing import Dict, Any, List, Tuple

import numpy as np
import joblib

# Keras import (TF-backed)
from keras.models import load_model

# local utils - these must exist in your repo
from utils.feature_extractor_login import extract_features_from_login
from utils.rules import compute_rule_risk_score

# ----------------- Logging -----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hybrid_predictor")

import yaml

# Load YAML config
try:
    with open("config.yaml", "r") as f:
        CONFIG = yaml.safe_load(f)
except Exception:
    CONFIG = {"thresholds": {}}
# ----------------- Load Profiles -----------------
DEFAULT_PROFILE = CONFIG.get("thresholds", {
    "ae_threshold": 0.03,         # default AE MSE threshold (needs calibration)
    "hybrid_threshold": 0.5,      # score (0..1) above which becomes suspicious
    "fraud_threshold": 0.85,      # score (0..1) above which becomes fraud
    "rule_weight": 0.3,           # weight given to rule_score (0..1)
    # IF mapping params (logistic) - calibrate on validation set
    "if_midpoint": 0.0,           # decision_function value at which logistic=0.5 (default 0)
    "if_steepness": 6.0,          # steepness of logistic (higher => sharper)
    # misc
    })

try:
    with open("profiles/risk_profiles.json", "r", encoding="utf-8") as f:
        PROFILES = json.load(f)
except Exception:
    logger.warning("profiles/risk_profiles.json not found or invalid; using default profile.")
    PROFILES = {"Default": DEFAULT_PROFILE}

# ----------------- Model Loading with safe fallbacks -----------------
MODEL_DIR = "saved_models"
if_model = None
scaler = None
ae_model = None

def _safe_load_models():
    global if_model, scaler, ae_model
    # Isolation Forest
    try:
        if_model = joblib.load(os.path.join(MODEL_DIR, "isolation_forest_model.pkl"))
        logger.info("Loaded IsolationForest model.")
    except Exception as e:
        logger.exception("Could not load IsolationForest model: %s", e)
        if_model = None

    # Scaler
    try:
        scaler = joblib.load(os.path.join(MODEL_DIR, "standard_scaler.pkl"))
        logger.info("Loaded scaler.")
    except Exception as e:
        logger.exception("Could not load scaler: %s", e)
        scaler = None

    # Autoencoder
    try:
        ae_model = load_model(os.path.join(MODEL_DIR, "autoencoder_model.h5"), compile=False)
        logger.info("Loaded Autoencoder model.")
    except Exception as e:
        logger.exception("Could not load Autoencoder model: %s", e)
        ae_model = None

_safe_load_models()

# ----------------- Helpers -----------------
def _build_numeric_vector(features: Dict[str, Any]) -> Tuple[np.ndarray, List[str]]:
    """
    Build numeric vector preserving the order of dict keys.
    Booleans -> 1/0, numeric -> float, others -> 0.0 (placeholder).
    Returns: (1, n) numpy array and ordered_keys list.
    """
    numeric = []
    ordered_keys = []
    for k, v in features.items():
        ordered_keys.append(k)
        if isinstance(v, bool):
            numeric.append(1.0 if v else 0.0)
        elif isinstance(v, (int, float, np.integer, np.floating)):
            try:
                numeric.append(float(v))
            except Exception:
                numeric.append(0.0)
        elif v is None:
            numeric.append(0.0)
        else:
            # categorical/string features should ideally be pre-encoded during feature extraction
            numeric.append(0.0)
    arr = np.array([numeric], dtype=np.float32)
    return arr, ordered_keys

def _if_raw_to_anomaly_score(if_raw: float, midpoint: float = 0.0, steepness: float = 6.0) -> float:
    """
    Convert IsolationForest decision_function value into anomaly score in [0,1].
    decision_function: higher -> more normal, lower (negative) -> more anomalous.
    We invert then pass through logistic to get stable mapping.

    Parameters:
     - if_raw: decision_function output for the sample (float)
     - midpoint: the if_raw value mapped to 0.5 (calibrate; default 0.0)
     - steepness: controls slope (higher -> sharper). Calibrate for your dataset.

    Returns:
     anomaly_score in [0,1], where 1.0 = most anomalous.
    """
    # invert so larger means more anomalous
    inverted = -float(if_raw)
    # logistic mapping centered at (midpoint inverted)
    # compute shift: we map inverted - (-midpoint) => inverted + midpoint
    x = inverted + float(midpoint)
    try:
        score = 1.0 / (1.0 + np.exp(-steepness * (x)))
    except Exception:
        score = 0.5 if inverted == 0 else (1.0 if inverted > 0 else 0.0)
    # Clip
    return float(np.clip(score, 0.0, 1.0))

def _ae_loss_to_score(ae_loss: float, ae_threshold: float) -> float:
    """
    Map AE reconstruction loss (MSE) to a 0..1 anomaly score.
    - If ae_loss <= (ae_threshold/2) -> small score near 0
    - If ae_loss >= (ae_threshold * 3) -> score near 1
    - Linear / smooth mapping between these points.
    """
    # Protect against zero threshold
    thr = max(ae_threshold, 1e-9)
    low = thr * 0.5
    high = thr * 3.0
    if ae_loss <= low:
        return 0.0
    if ae_loss >= high:
        return 1.0
    # linear between low..high
    return float((ae_loss - low) / (high - low))

def _clamp01(x: float) -> float:
    return float(min(1.0, max(0.0, x)))

# ----------------- Explanations -----------------
def _build_explanations(features: Dict[str, Any],
                        rule_score: float,
                        if_score: float,
                        ae_loss: float,
                        ae_threshold: float) -> List[str]:
    """
    Build human-friendly explanations. These are deterministic and tied to flags.
    """
    reasons = []
    # feature-driven reasons (keys depend on extract_features_from_login)
    if features.get("geo_mismatch"):
        reasons.append("GeoIP country does not match SIM/home country.")
    if features.get("device_imei_mismatch") or features.get("device_mismatch"):
        reasons.append("Device/IMEI mismatch from historical device for this account.")
    if features.get("new_device"):
        reasons.append("First-time login from a new/unknown device.")
    if features.get("vpn_detected") or features.get("vpn"):
        reasons.append("VPN or proxy detected for the IP.")
    if features.get("odd_hour"):
        reasons.append("Login at an unusual hour compared to user baseline.")
    if isinstance(features.get("ip_risk_score"), (int, float)) and features.get("ip_risk_score", 0) > 70:
        reasons.append("High IP reputation / blacklist score.")
    # ML-driven reasons
    if if_score >= 0.6:
        reasons.append("Isolation Forest anomaly score high.")
    if ae_loss > ae_threshold:
        reasons.append("Autoencoder reconstruction error exceeds threshold.")
    # rule-driven
    if rule_score >= 60:
        reasons.append("Rule engine produced a high weighted risk score.")
    if not reasons:
        reasons.append("No single red-flag, but combined risk is moderate/low.")
    return reasons

# ----------------- Main predictor -----------------
def hybrid_predict(login_event: Dict[str, Any], profile_name: str = "Default") -> Dict[str, Any]:
    """
    Input:
      login_event: raw JSON-style dictionary representing login/registration attempt
      profile_name: name from profiles JSON (fallback to 'Default')
    Output:
      dict with verdict, numeric scores, flags, explanations, feature_keys
    """
    # safe profile fetch
    profile = PROFILES.get(profile_name, PROFILES.get("Default", DEFAULT_PROFILE))
    ae_threshold = float(profile.get("ae_threshold", DEFAULT_PROFILE["ae_threshold"]))
    hybrid_threshold = float(profile.get("hybrid_threshold", DEFAULT_PROFILE["hybrid_threshold"]))
    fraud_threshold = float(profile.get("fraud_threshold", DEFAULT_PROFILE["fraud_threshold"]))
    rule_weight = float(profile.get("rule_weight", DEFAULT_PROFILE["rule_weight"]))
    # IF mapping params
    if_midpoint = float(profile.get("if_midpoint", DEFAULT_PROFILE.get("if_midpoint", 0.0)))
    if_steepness = float(profile.get("if_steepness", DEFAULT_PROFILE.get("if_steepness", 6.0)))

    # 1) extract features (should return a dict of named features)
    try:
        features = extract_features_from_login(login_event)
        if not isinstance(features, dict):
            logger.warning("extract_features_from_login did not return a dict; received %s", type(features))
            features = {}
    except Exception as e:
        logger.exception("Feature extraction failed: %s", e)
        features = {}

    # 2) build numeric vector
    try:
        numeric_vec, ordered_keys = _build_numeric_vector(features)
    except Exception as e:
        logger.exception("Error building numeric vector: %s", e)
        numeric_vec, ordered_keys = np.zeros((1, 1), dtype=np.float32), ["_placeholder"]

    # 3) scale vector if scaler present
    try:
        if scaler is not None:
            vec_scaled = scaler.transform(numeric_vec)
        else:
            vec_scaled = numeric_vec  # unscaled fallback
    except Exception as e:
        logger.exception("Scaler transform failed: %s", e)
        vec_scaled = numeric_vec

    # 4) Isolation Forest score -> map to anomaly score 0..1
    if_score_raw = None
    if_score = 0.0
    try:
        if if_model is not None:
            # decision_function: higher -> more normal. We convert via logistic to anomaly(0..1)
            if_raw = float(if_model.decision_function(vec_scaled)[0])
            if_score_raw = if_raw
            if_score = _if_raw_to_anomaly_score(if_raw, midpoint=if_midpoint, steepness=if_steepness)
        else:
            logger.debug("Isolation Forest model not loaded; skipping IF scoring.")
            if_score_raw = 0.0
            if_score = 0.0
    except Exception as e:
        logger.exception("IsolationForest scoring failed: %s", e)
        if_score_raw = 0.0
        if_score = 0.0

    # 5) Autoencoder reconstruction error (MSE) -> ae_loss (float)
    ae_loss = 0.0
    try:
        if ae_model is not None:
            # ae_model expects same-shaped input as used in training (scaled)
            ae_pred = ae_model.predict(vec_scaled, verbose=0)
            # compute mean squared error per sample
            ae_loss = float(np.mean(np.square(vec_scaled - ae_pred)))
        else:
            logger.debug("Autoencoder model not loaded; skipping AE scoring.")
            ae_loss = 0.0
    except Exception as e:
        logger.exception("Autoencoder prediction failed: %s", e)
        ae_loss = 0.0

    # 6) rule engine (expected to return (score, reasons) or score)
    rule_score = 0.0
    rule_reasons: List[str] = []
    try:
        r_out = compute_rule_risk_score(features)
        if isinstance(r_out, (list, tuple)):
            rule_score = float(r_out[0])
            if len(r_out) > 1:
                rule_reasons = r_out[1]
        elif isinstance(r_out, (int, float)):
            rule_score = float(r_out)
        else:
            logger.debug("Unexpected rule engine output type: %s", type(r_out))
    except Exception as e:
        logger.exception("Rule engine failed: %s", e)
        rule_score = 0.0
        rule_reasons = []

    # Normalize rule_score into 0..1 if it's on a 0..100 scale (detect heuristically)
    rule_score_norm = rule_score / 100.0 if rule_score > 1.0 else rule_score
    rule_score_norm = _clamp01(rule_score_norm)

    # 7) combine ML anomaly components (IF and AE) into a single anomaly_score (0..1)
    # Weighted mix: IF = 70%, AE = 30%
    ae_score = _ae_loss_to_score(ae_loss, ae_threshold)
    anomaly_score = (0.7 * if_score) + (0.3 * ae_score)
    anomaly_score = _clamp01(anomaly_score)

    # 8) final weighted score (0..1)
    final_score = (1.0 - rule_weight) * anomaly_score + rule_weight * rule_score_norm
    final_score = _clamp01(final_score)

    # 9) verdict thresholds (profile values expressed as 0..1)
    if final_score >= fraud_threshold:
        verdict = "fraud"
    elif final_score >= hybrid_threshold:
        verdict = "suspicious"
    else:
        verdict = "legit"

    # 10) build explanations (prefer rule_reasons if available)
    explanations = rule_reasons if rule_reasons else _build_explanations(features, rule_score, if_score, ae_loss, ae_threshold)

    result = {
        "verdict": verdict,
        "final_risk_score": round(float(final_score * 100.0), 2),  # percent 0..100 for display
        "anomaly_score": round(float(anomaly_score), 4),
        "if_score_raw": round(float(if_score_raw) if if_score_raw is not None else 0.0, 6),
        "if_anomaly_score": round(float(if_score), 4),
        "ae_loss": round(float(ae_loss), 6),
        "ae_score": round(float(ae_score), 4),
        "rule_score": round(float(rule_score), 2),
        "rule_score_norm": round(float(rule_score_norm), 4),
        "profile_used": profile_name,
        "explanations": explanations,
        "feature_keys": ordered_keys,
        "flags": {
            "ae_flag": bool(ae_loss > ae_threshold),
            "if_flag": bool(if_score >= 0.6),  # threshold for IF anomaly alert (tunable)
            "rule_flag": bool(rule_score_norm >= hybrid_threshold),
        }
    }

    # debug log (can be noisy; keep for calibration)
    logger.debug("hybrid_predict -> %s", {
        "if_raw": if_score_raw, "if_score": if_score, "ae_loss": ae_loss,
        "ae_score": ae_score, "rule_score": rule_score, "final_score": final_score
    })

    return result
# ----------------- End of module -----------------