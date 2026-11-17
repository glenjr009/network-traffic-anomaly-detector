"""
NetGuard AI - Real-Time API & RAG SOC Chatbot entry point.

Streamlit dashboard remains available via: streamlit run app.py
API server (detections WebSocket + chatbot): python run_api.py
"""

import os

import uvicorn

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() in ("true", "1", "yes")

    print("=" * 60)
    print("[*] NetGuard AI - Network Anomaly Detector & SOC Chatbot")
    print(f"[*] API Server: http://{host}:{port}")
    print(f"[*] Interactive Docs: http://{host}:{port}/docs")
    print(f"[*] RAG Status: http://{host}:{port}/api/rag/status")
    print(f"[*] Detections WS: ws://{host}:{port}/ws/detections")
    print("[*] Dashboard: streamlit run app.py")
    print("=" * 60)

    uvicorn.run("src.realtime_api:app", host=host, port=port, reload=reload)
