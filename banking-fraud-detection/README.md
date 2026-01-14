📱 BAIDS – Behavior-based Android Intrusion Detection System
📌 Project Overview

BAIDS is a machine learning–driven Android intrusion detection system that analyzes behavioral artifacts extracted from Android forensic logs such as SMS, network activity (IPDR/DNS), GPS movement, and application usage.
Instead of relying on signatures, BAIDS learns normal user behavior patterns and detects deviations that may indicate malware infection, account compromise, SIM spoofing, or stealthy intrusions.

The project is designed with a forensic-first mindset, emphasizing explainability, reproducibility, and multi-source evidence correlation.

🎯 Project Goals

Learn behavioral baselines from Android forensic data

Detect anomalies using ML and graph-based techniques

Support explainable, court-admissible ML outputs

Enable future research in behavior-based mobile security

🧠 Final Issue List (ML-Focused)
1. Baseline Anomaly Detection Benchmark

Implement simple statistical anomaly detection (Z-score / IQR) to establish a baseline for ML models.

2. Feature Distribution Visualization

Visualize feature distributions to understand data quality and detect skew or noise.

3. Feature Metadata Dictionary

Create a structured dictionary documenting each feature, its source, and interpretation.

4. Missing Data Handling for Forensic Logs

Implement consistent missing-value handling to stabilize ML pipelines.

5. Configurable Thresholds via YAML

Move hard-coded thresholds into configuration files for flexible experimentation.

6. Synthetic Normal Behavior Generator

Generate synthetic “normal” behavioral data to test anomaly detectors.

7. Unified Feature Scaling Pipeline

Normalize heterogeneous features to ensure fair ML model learning.

8. Multi-Modal Feature Fusion Model

Fuse features from SMS, GPS, and network logs into a unified ML model.

9. Graph-Based Behavior Modeling

Model device behavior as graphs and detect anomalous subgraphs using GNNs.

10. Ensemble Anomaly Scoring

Combine multiple anomaly detectors into a robust ensemble scoring system.