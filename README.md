# 🛡️ Network Traffic Anomaly Detector

### Machine Learning-Based Network Security Monitoring and Anomaly Detection System

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-F7931E?logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![Wireshark](https://img.shields.io/badge/Wireshark-TShark-1679A7?logo=wireshark&logoColor=white)](https://www.wireshark.org/)
[![Chrome Extension](https://img.shields.io/badge/Chrome-Extension-4285F4?logo=googlechrome&logoColor=white)](https://developer.chrome.com/docs/extensions/)
[![Status](https://img.shields.io/badge/Status-Active%20Development-orange)]()

---

## 📌 Overview

**Network Traffic Anomaly Detector** is a cybersecurity-focused machine learning system designed to identify anomalous network traffic and provide security-oriented analysis of detected events.

The project combines **network traffic capture, bidirectional flow extraction, machine learning, cybersecurity analysis, risk scoring, and real-time monitoring** into a single detection pipeline.

The system is designed around the following workflow:

```text
Network Traffic
      │
      ▼
Packet Capture
(TShark / Wireshark)
      │
      ▼
Flow Construction
      │
      ▼
CICIDS-Style Feature Extraction
      │
      ▼
78 Flow Features
      │
      ▼
Random Forest Classifier
      │
      ▼
BENIGN / ATTACK
      │
      ▼
Cybersecurity Analysis
      │
      ├── Threat Mapping
      ├── Risk Scoring
      ├── Severity
      └── Recommendations
      │
      ▼
FastAPI Backend
      │
      ▼
WebSocket
      │
      ▼
Chrome Security Dashboard
