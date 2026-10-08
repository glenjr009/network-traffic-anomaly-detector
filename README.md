# 🛡️ Network Traffic Anomaly Detector

> An ML-powered network security system for detecting anomalous network traffic from flow-level features and presenting security insights through a real-time monitoring interface.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)
![Scikit--learn](https://img.shields.io/badge/scikit--learn-Machine%20Learning-F7931E?logo=scikit-learn)
![Wireshark](https://img.shields.io/badge/Wireshark-TShark-1679A7?logo=wireshark)
![Chrome Extension](https://img.shields.io/badge/Chrome-Extension-4285F4?logo=googlechrome)
![Status](https://img.shields.io/badge/Status-In%20Development-orange)

---

## 📌 Overview

**Network Traffic Anomaly Detector** is a cybersecurity-focused machine learning project designed to identify abnormal network traffic and assist analysts in understanding potentially malicious activity.

The system combines:

- Network traffic capture
- Bidirectional flow extraction
- CICIDS-style feature engineering
- Machine learning-based anomaly detection
- Security risk analysis
- Real-time backend communication
- Browser-based security monitoring

The current machine learning pipeline uses a **Random Forest classifier** trained on CICIDS-2017-derived flow features.

The current ML classifier performs **binary classification**:

```text
BENIGN
   │
   └── Normal network traffic

ATTACK
   │
   └── Suspicious / malicious traffic
