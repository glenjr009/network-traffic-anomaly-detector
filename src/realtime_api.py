import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.live_capture import LiveCapture

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# DETECTION HUB (WEBSOCKET BROADCAST)
# ============================================================

class DetectionHub:
    """Broadcast detections to every connected WebSocket client."""

    def __init__(self, loop):
        self.loop = loop
        self.subscribers = set()

    def subscribe(self):
        queue = asyncio.Queue(maxsize=100)
        self.subscribers.add(queue)
        return queue

    def unsubscribe(self, queue):
        self.subscribers.discard(queue)

    def publish_from_thread(self, event):
        # Called by the capture thread; mutate asyncio queues on the event loop.
        self.loop.call_soon_threadsafe(self._broadcast, event)

    def _broadcast(self, event):
        for queue in tuple(self.subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass

            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Dropping detection because a client queue is full")


# ============================================================
# RAG RETRIEVER SINGLETON
# ============================================================

_rag_retriever = None


def get_rag_retriever():
    """Lazily load and cache the RAGRetriever instance."""
    global _rag_retriever
    if _rag_retriever is None:
        try:
            from src.rag import RAGRetriever, default_config
            _rag_retriever = RAGRetriever(default_config)
            logger.info(
                "RAGRetriever initialized with %d indexed chunks",
                len(_rag_retriever.vector_store.chunks),
            )
        except Exception:
            logger.exception("Could not initialize RAGRetriever")
            _rag_retriever = None
    return _rag_retriever


# ============================================================
# FASTAPI LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    app.state.detection_hub = DetectionHub(loop)
    app.state.capture = None

    # Pre-warm RAG retriever in background
    try:
        get_rag_retriever()
    except Exception:
        logger.warning("RAG system pre-warming failed; will retry on first query")

    enabled = os.getenv("NAD_ENABLE_CAPTURE", "0") == "1"

    if enabled:
        try:
            interface_index = int(os.getenv("NAD_INTERFACE_INDEX", "18"))
            capture = LiveCapture(
                interface_index=interface_index,
                publish=app.state.detection_hub.publish_from_thread,
            )
            capture.start()
            app.state.capture = capture
            logger.info("Live capture enabled on interface %s", interface_index)
        except Exception:
            logger.exception("Could not start live capture")
    else:
        logger.warning(
            "Live capture is disabled. Set NAD_ENABLE_CAPTURE=1 to enable it."
        )

    try:
        yield
    finally:
        if getattr(app.state, "capture", None) is not None:
            app.state.capture.stop()


app = FastAPI(
    title="Network Anomaly Detector - Real-Time API & RAG SOC Assistant",
    lifespan=lifespan,
)


def _cors_allowed_origins() -> List[str]:
    """Explicit localhost/dashboard origins only — never combine '*' with credentials."""
    configured = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:8501",
        "http://localhost:8501",
    ]


# CORS for local dashboard + Chrome extension pages (no wildcard with credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allowed_origins(),
    allow_origin_regex=r"^chrome-extension://[a-p]{32}$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


# ============================================================
# PYDANTIC SCHEMAS FOR CHATBOT
# ============================================================

class ChatRequest(BaseModel):
    query: str = Field(..., description="Cybersecurity query or telemetry question")
    prediction: Optional[Dict[str, Any]] = Field(
        None, description="Optional ML prediction telemetry"
    )


class ExplainDetectionRequest(BaseModel):
    detection: Dict[str, Any] = Field(
        ..., description="Telemetry event dictionary from anomaly detector"
    )
    question: Optional[str] = Field(
        "Explain this detected network anomaly and provide recommended mitigations.",
        description="Inquiry question",
    )


class ChatResponse(BaseModel):
    query: str
    answer: str
    sources: List[Dict[str, Any]]
    has_evidence: bool
    latency_ms: float
    mode: str


# ============================================================
# CORE ENDPOINTS
# ============================================================

@app.get("/")
def root():
    capture = getattr(app.state, "capture", None)
    capture_enabled = (
        capture is not None
        and capture.thread is not None
        and capture.thread.is_alive()
    )
    return {
        "status": "online",
        "service": "Real-Time Network Anomaly Detector & RAG SOC Assistant",
        "capture_enabled": capture_enabled,
        "rag_available": get_rag_retriever() is not None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.websocket("/ws/detections")
async def detection_stream(websocket: WebSocket):
    await websocket.accept()
    hub = getattr(websocket.app.state, "detection_hub", None)
    if not hub:
        await websocket.close()
        return
    queue = hub.subscribe()

    logger.info("Extension connected to detection stream")

    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        logger.info("Extension disconnected")
    finally:
        hub.unsubscribe(queue)


# ============================================================
# CHATBOT & RAG SOC ASSISTANT ENDPOINTS
# ============================================================

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    RAG-grounded conversational assistant endpoint.
    Answers cybersecurity inquiries using local documentation evidence,
    calling configured LLMs with multi-provider fallback or clean offline responses.
    """
    start_time = time.time()
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    from src.rag import (
        call_llm,
        build_general_prompt,
        build_prediction_prompt,
        build_offline_fallback,
        is_out_of_domain,
        OUT_OF_DOMAIN_REFUSAL,
        default_config,
    )

    # Fast guardrail: refuse out-of-domain requests without telemetry
    if is_out_of_domain(query) and not request.prediction:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return ChatResponse(
            query=query,
            answer=OUT_OF_DOMAIN_REFUSAL,
            sources=[],
            has_evidence=False,
            latency_ms=latency_ms,
            mode="out_of_domain_refusal",
        )

    retriever = get_rag_retriever()
    if retriever:
        retrieval_result = retriever.retrieve(query)
    else:
        retrieval_result = {
            "has_evidence": False,
            "sources": [],
            "context_text": "",
        }

    # Prompt assembly with Three-Level Grounding
    if request.prediction:
        prompt = build_prediction_prompt(
            query=query,
            retrieval_result=retrieval_result,
            prediction=request.prediction,
        )
    else:
        prompt = build_general_prompt(
            query=query,
            retrieval_result=retrieval_result,
        )

    # Attempt LLM generation
    llm_answer = call_llm(prompt, default_config)

    if llm_answer:
        answer = llm_answer
        provider_name = str(getattr(default_config, "LLM_PROVIDER", "auto"))
        mode = f"llm_{provider_name}"
    else:
        # Fall back to grounded knowledge base citations
        answer = build_offline_fallback(
            prediction=request.prediction,
            retrieval_result=retrieval_result,
        )
        mode = "offline_knowledge_base"

    latency_ms = round((time.time() - start_time) * 1000, 2)
    return ChatResponse(
        query=query,
        answer=answer,
        sources=retrieval_result.get("sources", []),
        has_evidence=bool(retrieval_result.get("has_evidence", False)),
        latency_ms=latency_ms,
        mode=mode,
    )


@app.post("/api/chat/explain", response_model=ChatResponse)
async def explain_detection_endpoint(request: ExplainDetectionRequest):
    """
    Explain a specific anomaly detection event using ML telemetry and RAG SOC knowledge.
    """
    question = request.question or "Explain this network detection event and provide mitigation steps."
    chat_req = ChatRequest(query=question, prediction=request.detection)
    return await chat_endpoint(chat_req)


@app.get("/api/rag/status")
def rag_status():
    """Returns runtime status of RAG index and LLM configurations."""
    from src.rag import default_config

    retriever = get_rag_retriever()
    chunk_count = len(retriever.vector_store.chunks) if retriever else 0
    return {
        "status": "online" if retriever else "error",
        "chunks_indexed": chunk_count,
        "llm_provider": getattr(default_config, "LLM_PROVIDER", "auto"),
        "gemini_configured": bool(getattr(default_config, "GEMINI_API_KEY", "")),
        "openai_configured": bool(getattr(default_config, "OPENAI_API_KEY", "")),
        "groq_configured": bool(getattr(default_config, "GROQ_API_KEY", "")),
        "gemini_model": getattr(default_config, "GEMINI_MODEL", ""),
        "openai_model": getattr(default_config, "OPENAI_MODEL", ""),
        "groq_model": getattr(default_config, "GROQ_MODEL", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.realtime_api:app", host="127.0.0.1", port=8000, reload=True)
