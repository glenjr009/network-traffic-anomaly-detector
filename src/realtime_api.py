
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from src.live_capture import LiveCapture

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    app.state.detection_hub = DetectionHub(loop)
    app.state.capture = None

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
        if app.state.capture is not None:
            app.state.capture.stop()


app = FastAPI(
    title="Network Anomaly Detector - Real-Time API",
    lifespan=lifespan,
)


@app.get("/")
def root():
    capture_enabled = (
        app.state.capture is not None
        and app.state.capture.thread is not None
        and app.state.capture.thread.is_alive()
    )
    return {
        "status": "online",
        "service": "Real-Time Network Anomaly Detector",
        "capture_enabled": capture_enabled,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.websocket("/ws/detections")
async def detection_stream(websocket: WebSocket):
    await websocket.accept()
    hub = websocket.app.state.detection_hub
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
