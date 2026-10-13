# 🛡️ Network Traffic Anomaly Detector

**A machine-learning-based network security monitoring and anomaly detection system.**

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![scikit-learn](https://img.shields.io/badge/ML-scikit--learn-orange?logo=scikitlearn)](https://scikit-learn.org/)
[![Wireshark](https://img.shields.io/badge/Traffic-Wireshark-1679A7?logo=wireshark)](https://www.wireshark.org/)
[![Chrome Extension](https://img.shields.io/badge/Interface-Chrome%20Extension-4285F4?logo=googlechrome)](https://developer.chrome.com/docs/extensions/)
[![Status](https://img.shields.io/badge/Status-Active%20Development-orange)]()

Network Traffic Anomaly Detector is a cybersecurity project that uses machine learning to classify network traffic as **BENIGN** or **ATTACK**. It combines network-flow feature extraction, trained machine-learning models, risk assessment, and security-oriented recommendations to support network monitoring and investigation.

> **Project status:** Core ML inference and cybersecurity analysis components are available. End-to-end live packet capture, continuous inference, and dashboard integration are still being developed and validated.

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Objectives](#-objectives)
- [Architecture](#-architecture)
- [Key Features](#-key-features)
- [Technology Stack](#-technology-stack)
- [Machine Learning](#-machine-learning)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Running the API](#-running-the-api)
- [Traffic Analysis Workflow](#-traffic-analysis-workflow)
- [Chrome Extension](#-chrome-extension)
- [Testing](#-testing)
- [Limitations](#-limitations)
- [Roadmap](#-roadmap)
- [Security and Responsible Use](#-security-and-responsible-use)
- [Contributing](#-contributing)
- [License](#-license)

## 📖 Overview

Network traffic contains useful signals about communication patterns, connection behaviour, packet sizes, protocols, and potential security threats. Analysing these signals can help identify traffic that differs from patterns learned during model training.

This project aims to build a pipeline that transforms network traffic into flow-level features, applies a trained Random Forest classifier, and enriches the resulting predictions with security context.

The intended workflow is:

1. Capture or load network traffic.
2. Parse supported packets and construct network flows.
3. Extract the required CICIDS-style flow features.
4. Validate the feature schema and run model inference.
5. Classify each flow as BENIGN or ATTACK.
6. Calculate risk and generate security recommendations.
7. Present detection results through an API and security interface.

## 🎯 Objectives

- Develop a machine-learning-based network anomaly detection pipeline.
- Extract flow-level features compatible with the trained CICIDS model.
- Validate feature names, ordering, units, and numerical values before inference.
- Enrich predictions with risk scoring and security recommendations.
- Provide an interface for inspecting detection events.
- Establish a testable foundation for continuous network monitoring.

## 🏗️ Architecture

```text
       Network Traffic
              |
              v
    Packet Capture / PCAP
              |
              v
      Packet Processing
              |
              v
       Flow Construction
              |
              v
     CICIDS Feature Extraction
          (78 Features)
              |
              v
      Random Forest Model
              |
              v
      BENIGN / ATTACK
              |
              v
      Security Analysis
       /      |       \
      v       v        v
    Risk   Severity  Recommendations
       \      |       /
              v
       FastAPI Backend
              |
              v
          WebSocket
              |
              v
     Chrome Security Interface
```

**Integration note:** This diagram represents the intended end-to-end architecture. The components are not yet all connected into one continuously operating live-detection pipeline.

## ✨ Key Features

### 1. Machine Learning Inference

- Uses a trained Random Forest model for binary traffic classification.
- Supports the expected 78-feature CICIDS-style input schema.
- Validates feature count, names, ordering, numeric types, and non-finite values.
- Returns a prediction, confidence score, and model identifier.

### 2. Network Flow Feature Extraction

The feature extraction pipeline is designed to calculate network-flow statistics, including:

- Forward and backward packet counts.
- Packet lengths and packet-length statistics.
- Flow duration and inter-arrival times.
- Packet and byte rates.
- TCP flag statistics.
- Active and idle time statistics.
- Directional bulk-transfer statistics.

Feature compatibility with the trained model is essential: having 78 values alone does not guarantee that the model receives the correct information.

### 3. Cybersecurity Analysis

The security-analysis layer provides supporting context for detected events, including:

- Threat or anomaly mapping.
- Risk scoring.
- Severity assessment.
- Security recommendations.
- Packet and flow metadata for investigation.

These results support investigation and prioritisation. They should not be interpreted as proof that a particular attack occurred.

### 4. FastAPI Backend

The backend provides an HTTP API and a WebSocket endpoint intended to deliver detection events to connected clients.

The current WebSocket implementation includes simulated events for interface testing. It must be connected to the actual capture and inference pipeline before it can be described as a real-time ML alert stream.

### 5. Chrome Extension

The Chrome extension provides a lightweight interface for viewing detection-event information received from the backend.

It is intended to display information such as prediction status, confidence, severity, timestamps, and related event details. The accuracy of displayed information depends on the data supplied by the backend.

## 🧰 Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python |
| Machine learning | scikit-learn, NumPy, pandas |
| Model serialization | Joblib / serialized model artifacts |
| Packet analysis | Wireshark / TShark |
| Saved packet capture parsing | Scapy, where enabled |
| Backend API | FastAPI |
| ASGI server | Uvicorn |
| Client interface | Chrome Extension, Manifest V3 |
| Testing | pytest |
| Source control | Git and GitHub |

## 🤖 Machine Learning

The project includes trained model artifacts for CICIDS-based and NSL-KDD-based experiments.

The live flow-inference integration work focuses on the existing CICIDS Random Forest model.

### CICIDS inference pipeline

```text
Extracted Network Flow
         |
         v
Feature Validation
         |
         v
Canonical 78-Feature Schema
         |
         v
Trained Random Forest
         |
         v
Prediction + Confidence
```

The CICIDS inference interface produces two classes:

- `BENIGN` — the model classifies the flow as benign.
- `ATTACK` — the model classifies the flow as an attack.

**Important:** The binary CICIDS model does not independently identify a specific attack family such as DDoS or port scanning. A binary `ATTACK` result must not automatically be labelled as one of those attack types without additional evidence or a separately validated classifier.

Model confidence is not a guarantee of correctness. Performance measured on a training or test dataset does not necessarily represent performance on previously unseen real-world traffic.

## 📂 Project Structure

```text
network-traffic-anomaly-detector/
│
├── data/                   # Dataset files, when included locally
├── docs/                   # Project and technical documentation
├── extension/              # Chrome extension
├── models/                 # Trained model artifacts and encoders
├── notebooks/              # Model training and experimentation
├── reports/                # Evaluation and validation reports
├── scripts/                # Validation and utility scripts
├── src/
│   ├── prediction.py       # Model loading and inference
│   ├── security_analysis.py# Security analysis integration
│   ├── attack_mapping.py   # Threat/anomaly mapping
│   ├── risk_scoring.py     # Risk calculation
│   └── realtime_api.py     # FastAPI and WebSocket endpoint
│
├── tests/                  # Automated tests
├── requirements.txt        # Python dependencies
├── .gitignore
└── README.md
```

Additional modules may be present on individual development branches. The structure above highlights the main project areas rather than guaranteeing that every optional module exists on every branch.

## 🚀 Getting Started

### Prerequisites

Install the following:

- Python 3.11 or a compatible Python version supported by the installed dependencies.
- Git.
- Wireshark/TShark if you intend to capture or inspect network traffic.
- Google Chrome if you intend to load the extension.

### 1. Clone the repository

```bash
git clone https://github.com/glenjr009/network-traffic-anomaly-detector.git
cd network-traffic-anomaly-detector
```

### 2. Create a virtual environment

**Windows PowerShell**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can invoke the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

**Linux / Kali Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

The root requirements file may not include every optional backend, packet-parsing, or dashboard dependency. Install additional packages only as required by the module you are running and the project's maintained dependency configuration.

For the saved-PCAP parser, install Scapy if it is not already installed:

```bash
python -m pip install scapy
```

For the FastAPI backend, if these packages are not included in your active requirements:

```bash
python -m pip install fastapi "uvicorn[standard]"
```

### 4. Verify the model artifacts

Check that the expected model files exist:

```text
models/
├── cicids_anomaly_model.pkl
├── cicids_label_encoder.pkl
├── nsl-kdd_anomaly_model.pkl
└── nsl-kdd_label_encoder.pkl
```

The CICIDS inference module requires its model and corresponding label encoder. If an artifact is missing, check the repository's model setup instructions before attempting inference.

**Security note:** Only load serialized model files from trusted sources. Pickle/joblib artifacts can execute code when deserialized.

## ▶️ Running the API

From the repository root, activate your virtual environment and start the FastAPI server:

```bash
python -m uvicorn src.realtime_api:app --reload
```

The development server should be available at:

- API root: `http://127.0.0.1:8000/`
- Interactive API documentation: `http://127.0.0.1:8000/docs`
- WebSocket endpoint: `ws://127.0.0.1:8000/ws/detections`

The API root can be used to check whether the server is responding.

**Current behaviour:** The existing WebSocket endpoint sends simulated events for testing. Starting the API does not, by itself, start packet capture or establish that real network traffic is being classified.

Use `--reload` for local development only.

## 🔬 Traffic Analysis Workflow

The project is intended to support both saved packet-capture analysis and, after integration, continuous monitoring.

### Saved PCAP / PCAPNG analysis

The development branch for live ML inference includes a saved-capture reader and validation tooling. These components are not available in `main` until their pull request is merged.

After checking out the branch containing those files and installing its required dependencies, inspect the available command-line options:

```bash
python scripts/validate_pcap.py --help
```

Follow the options and input requirements reported by that script to validate a capture.

Use only captures you own or are authorised to analyse. A successful saved-capture run demonstrates that the tested file can pass through the supported processing pipeline; it does not demonstrate continuous live capture or reliable attack detection in production.

## 🧩 Chrome Extension

The extension source is located in `extension/`.

To load it for local development:

1. Start the FastAPI server.
2. Open `chrome://extensions` in Chrome.
3. Enable **Developer mode**.
4. Select **Load unpacked**.
5. Choose the repository's `extension/` directory.
6. Open the extension and verify that it can connect to the configured backend.

The extension's WebSocket URL and expected event schema must match the backend. If the connection fails, inspect the extension service-worker console and the backend terminal.

Because the current backend uses simulated events, extension behaviour observed with those events should be reported as interface testing, not as evidence of real network threat detection.

## 🧪 Testing

Run the available automated tests from the repository root:

```bash
python -m pytest -v
```

To run a particular test module:

```bash
python -m pytest tests/test_prediction.py -v
```

The exact test files may differ by branch. Ensure that the dependencies and test fixtures for the selected branch are installed before interpreting the result.

Recommended validation checks include:

- Model artifacts load successfully.
- Input features match the canonical schema and expected ordering.
- Invalid NaN and infinite values are rejected appropriately.
- Flow calculations are tested against reference implementations where applicable.
- Saved-PCAP parsing handles supported packets and reports unsupported traffic.
- Prediction output uses the expected binary labels.
- The API sends real inference results once the live pipeline is integrated.
- The extension displays the same event values emitted by the backend.

No test should be described as passing unless it has actually been executed and its result recorded.

## ⚠️ Limitations

The following limitations should be considered when interpreting results:

1. **Live capture integration:** Continuous capture, flow construction, inference, and WebSocket delivery must be validated as one end-to-end pipeline.
2. **Binary classification:** The CICIDS model returns BENIGN or ATTACK, not a verified attack-family label.
3. **Dataset generalisation:** Performance on benchmark datasets may not transfer to arbitrary real-world networks.
4. **Feature compatibility:** Incorrect flow calculations or units can change predictions even when the feature count is correct.
5. **Confidence scores:** Model confidence does not equal the probability that an incident is genuine.
6. **Packet visibility:** Encrypted traffic, unsupported protocols, capture permissions, and missing packets can limit analysis.
7. **Automatic response:** Detection results should be reviewed before any firewall blocking or other disruptive response is attempted.

## 🗺️ Roadmap

- [x] Train and maintain machine-learning model artifacts.
- [x] Implement model inference and input validation.
- [x] Develop security-analysis and risk-scoring modules.
- [x] Build the Chrome extension interface.
- [ ] Complete review and merge of the saved-PCAP / flow-inference integration.
- [ ] Standardise project dependencies and setup instructions.
- [ ] Connect genuine packet-capture output to the inference pipeline.
- [ ] Replace simulated WebSocket events with actual model predictions.
- [ ] Complete dashboard integration.
- [ ] Validate end-to-end detection with authorised captures and labelled test traffic.
- [ ] Add continuous integration and reproducible test reporting.
- [ ] Evaluate false-positive rates and generalisation on independent datasets.

## 🔐 Security and Responsible Use

This project is intended for educational, research, and authorised defensive security monitoring.

- Capture traffic only on systems and networks for which you have permission.
- Protect PCAP files because they may contain sensitive metadata or application information.
- Do not expose the development API or WebSocket endpoint publicly without appropriate authentication, access controls, and transport security.
- Treat model output as an investigative signal rather than definitive proof of malicious activity.
- Do not enable automatic blocking or disruptive mitigation without testing, safeguards, and explicit authorisation.

## 🤝 Contributing

Contributions are welcome.

1. Create a feature branch from the appropriate base branch.
2. Keep changes focused on a clearly defined task.
3. Add or update tests for modified behaviour.
4. Update documentation when commands, dependencies, or APIs change.
5. Run the relevant tests and report their actual results.
6. Open a pull request with a summary, implementation details, and validation evidence.

Avoid committing virtual environments, generated bytecode, private captures, credentials, or large datasets that should be obtained separately.

## 📄 License

Add a `LICENSE` file and update this section with the chosen licence before presenting the project as openly licensed for reuse.

---

**Developed as a cybersecurity and machine-learning project focused on network-flow analysis, anomaly detection, and security-event investigation.**
