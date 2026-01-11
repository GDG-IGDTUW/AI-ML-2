def compute_rule_risk_score(features):
    """
    Compute a rule-based risk score between 0 and 1 based on high-weight risk indicators.
    Each flag contributes to the overall risk proportionally.
    """
    # Rule weights (tunable)
    rule_weights = {
        "imei_change_flag": 0.1,
        "imsi_change_flag": 0.1,
        "android_id_mismatch": 0.05,
        "device_model_mismatch": 0.05,
        "sim_slot_change_detected": 0.05,
        "is_emulator": 0.1,

        "ip_asn_mismatch": 0.05,
        "asn_risky": 0.1,
        "ip_country_mismatch": 0.05,
        "ip_blacklisted_flag": 0.1,
        "vpn_detected_flag": 0.05,
        "carrier_mismatch": 0.05,

        "gps_jump_distance_km": 0.05,  # continuous feature, normalize below
        "odd_hour_flag": 0.02,
        "weekday_vs_weekend": 0.02,
        "location_cluster_drift_flag": 0.05,

        "latency_score": 0.02,
        "session_token_reused": 0.02,
        "multiple_login_attempts": 0.03,
        "session_device_consistency": -0.05,
        "app_version_mismatch": 0.02,

        "unknown_device_flag": 0.05,
        "anomalous_login_ratio": 0.05
    }

    score = 0.0

# Apply rules
    for key, weight in rule_weights.items():
        if key in features:
            val = features[key]
            if key == "gps_jump_distance_km":
                score += weight * min(features[key] / 100, 1.0)  # normalize to [0,1]
            elif key == "latency_score":
                score += weight * (features[key] / 5.0)
            elif key == "anomalous_login_ratio":
                score += weight * features[key]
            else:
                score += weight * val

    return max(0.0, min(round(score, 3), 1.0))