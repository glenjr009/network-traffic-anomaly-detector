
import asyncio
import json
import websockets


async def main():
    uri = "ws://127.0.0.1:8000/ws/detections"
    print(f"Connecting to {uri}...")

    async with websockets.connect(uri) as ws:
        print("Connected. Waiting for a detection...")
        message = await asyncio.wait_for(ws.recv(), timeout=30)
        detection = json.loads(message)
        print(json.dumps(detection, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
