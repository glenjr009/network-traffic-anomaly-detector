# network-traffic-anomaly-detector
Machine learning based network traffic anomaly detector with dashboard and security score
              NETWORK
                 │
                 ▼
        ┌─────────────────┐
        │ Packet Capture  │
        │ Wireshark/      │
        │ tcpdump         │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Preprocessing   │
        │                 │
        │ Clean data      │
        │ Normalize       │
        │ Encode          │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Feature         │
        │ Extraction      │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ ML Detection    │
        │ Engine          │
        │                 │
        │ Random Forest   │
        │ / SVM etc.      │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Classification  │
        │                 │
        │ NORMAL          │
        │       or        │
        │ ANOMALY         │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Alert / Report  │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Dashboard /     │
        │ Extension       │
        └─────────────────┘