# utils/feature_extractor_login.py
# ==========================================
# Robust feature extractor for BAIDS
# Handles messy real-world login/registration events
# ==========================================

import math

def canonicalize_event(event: dict) -> dict:
    """
    Normalize keys so downstream feature extraction never breaks.
    Adds fallback values for missing fields.
    """

    # Canonical keys
    normalized = {
        "imei": event.get("imei"),
        "prev_imei": event.get("prev_imei", event.get("imei")),
        "imsi": event.get("imsi"),
        "prev_imsi": event.get("prev_imsi", event.get("imsi")),
        "android_id": event.get("android_id"),
        "prev_android_id": event.get("prev_android_id", event.get("android_id")),
        "device_model": event.get("device_model"),
        "prev_device_model": event.get("prev_device_model", event.get("device_model")),
        "sim_slot": event.get("sim_slot"),
        "prev_sim_slot": event.get("prev_sim_slot", event.get("sim_slot")),
        "is_rooted": event.get("is_rooted", False),

        # Network
        "ip_address": event.get("ip") or event.get("ip_address"),
        "ip_asn": event.get("ip_asn"),
        "prev_ip_asn": event.get("prev_ip_asn", event.get("ip_asn")),
        "sim_country": event.get("sim_country", "IN"),
        "ip_country": event.get("ip_country", "IN"),
        "sim_carrier": event.get("sim_carrier", "DefaultCarrier"),
        "ip_carrier": event.get("ip_carrier", "DefaultCarrier"),
        "vpn_detected": event.get("vpn_detected", False),

        # Geo
        "geo_ip_distance_km": event.get("geo_ip_distance_km", 0.0),
        "gps_jump_distance_km": event.get("gps_jump_distance_km", 0.0),
        "is_weekend": event.get("is_weekend", False),
        "prev_is_weekend": event.get("prev_is_weekend", False),
        "location_cluster_id": event.get("location_cluster_id", -1),
        "known_location_clusters": event.get("known_location_clusters", []),

        # Time
        "login_time_local_hour": event.get("login_time_local_hour", 12),

        # Session / App
        "login_latency_ms": event.get("login_latency_ms", 0),
        "session_token": event.get("session_token"),
        "previous_tokens": event.get("previous_tokens", []),
        "multiple_login_attempts": event.get("multiple_login_attempts", 0),
        "device_id": event.get("device_id"),
        "trusted_device_ids": event.get("trusted_device_ids", []),
        "app_version": event.get("app_version", "1.0"),
        "expected_app_version": event.get("expected_app_version", "1.0"),

        # User account history
        "login_count_past_7_days": event.get("login_count_past_7_days", 0),
        "anomalous_login_ratio": event.get("anomalous_login_ratio", 0.0),
        "known_device_ids": event.get("known_device_ids", []),
    }

    return normalized


def extract_features_from_login(login_event: dict) -> dict:
    """
    Extracts engineered features for anomaly/fraud detection.
    Safe defaults ensure missing keys don't break flow.
    """

    e = canonicalize_event(login_event)

    # Device & SIM fingerprint
    imei_change_flag = int(e["imei"] != e["prev_imei"])
    imsi_change_flag = int(e["imsi"] != e["prev_imsi"])
    android_id_mismatch = int(e["android_id"] != e["prev_android_id"])
    device_model_mismatch = int(e["device_model"] != e["prev_device_model"])
    sim_slot_change_detected = int(e["sim_slot"] != e["prev_sim_slot"])

    device_model = str(e.get("device_model", "")).lower()
    is_rooted = bool(e.get("is_rooted", False))
    is_emulator = int("emulator" in device_model or is_rooted)

    # Network & IP intelligence
    ip_asn_mismatch = int(e["ip_asn"] != e["prev_ip_asn"])
    risky_asns = set(e.get("risky_asns", []))
    asn_risky = int(e["ip_asn"] in risky_asns)
    ip_country_mismatch = int(e["ip_country"] != e["sim_country"])

    ip_blacklist = set(e.get("ip_blacklist", []))
    ip_blacklisted_flag = int(e["ip_address"] in ip_blacklist)

    geo_ip_distance_km = float(e.get("geo_ip_distance_km", 0.0))
    vpn_detected_flag = int(e.get("vpn_detected", False))
    carrier_mismatch = int(e["sim_carrier"] != e["ip_carrier"])

    # Geo & behavioral drift
    gps_jump_distance_km = float(e.get("gps_jump_distance_km", 0.0))
    login_time_local_hour = int(e.get("login_time_local_hour", 12))
    odd_hour_flag = int(login_time_local_hour in [0, 1, 2, 3, 4])

    weekday_vs_weekend = int(e["is_weekend"] != e["prev_is_weekend"])
    location_cluster_id = e.get("location_cluster_id", -1)
    known_clusters = set(e.get("known_location_clusters", []))
    location_cluster_drift_flag = int(location_cluster_id not in known_clusters)

    # Session / latency / app behavior
    login_latency_ms = int(e.get("login_latency_ms", 0))
    latency_score = min(math.ceil(login_latency_ms / 250), 5)
    session_token_reused = int(e["session_token"] in e["previous_tokens"])
    multiple_login_attempts = int(e.get("multiple_login_attempts", 0))
    session_device_consistency = int(e["device_id"] in e["trusted_device_ids"])
    app_version_mismatch = int(e["app_version"] != e["expected_app_version"])

    # User account history
    login_count_past_7_days = int(e.get("login_count_past_7_days", 0))
    anomalous_login_ratio = float(e.get("anomalous_login_ratio", 0.0))
    known_devices_count = len(e.get("known_device_ids", []))
    unknown_device_flag = int(e["device_id"] not in e["known_device_ids"])

    # Final features dict
    features = {
        "imei_change_flag": imei_change_flag,
        "imsi_change_flag": imsi_change_flag,
        "android_id_mismatch": android_id_mismatch,
        "device_model_mismatch": device_model_mismatch,
        "sim_slot_change_detected": sim_slot_change_detected,
        "is_emulator": is_emulator,
        "ip_asn_mismatch": ip_asn_mismatch,
        "asn_risky": asn_risky,
        "ip_country_mismatch": ip_country_mismatch,
        "ip_blacklisted_flag": ip_blacklisted_flag,
        "geo_ip_distance_km": geo_ip_distance_km,
        "vpn_detected_flag": vpn_detected_flag,
        "carrier_mismatch": carrier_mismatch,
        "gps_jump_distance_km": gps_jump_distance_km,
        "login_time_local_hour": login_time_local_hour,
        "odd_hour_flag": odd_hour_flag,
        "weekday_vs_weekend": weekday_vs_weekend,
        "location_cluster_id": location_cluster_id,
        "location_cluster_drift_flag": location_cluster_drift_flag,
        "login_latency_ms": login_latency_ms,
        "latency_score": latency_score,
        "session_token_reused": session_token_reused,
        "multiple_login_attempts": multiple_login_attempts,
        "session_device_consistency": session_device_consistency,
        "app_version_mismatch": app_version_mismatch,
        "login_count_past_7_days": login_count_past_7_days,
        "anomalous_login_ratio": anomalous_login_ratio,
        "known_devices_count": known_devices_count,
        "unknown_device_flag": unknown_device_flag,
    }

    return features
