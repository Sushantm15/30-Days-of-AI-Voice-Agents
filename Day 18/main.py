import os
import asyncio
import websockets
import json
import base64
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv()
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

# FastAPI app
app = FastAPI()

# Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HTML_FILE = "index.html"

# Serve frontend
@app.get("/")
async def get():
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Connect to AssemblyAI real-time API (with turn detection)
    uri = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000&model=universal&enable_turn_detection=true"
    async with websockets.connect(
        uri,
        extra_headers={"Authorization": ASSEMBLYAI_API_KEY},
        ping_interval=5,
        ping_timeout=20
    ) as assembly_ws:

        async def receive_from_client():
            try:
                while True:
                    data = await websocket.receive_bytes()
                    b64_audio = base64.b64encode(data).decode("utf-8")
                    payload = json.dumps({"audio_data": b64_audio})
                    await assembly_ws.send(payload)
            except Exception:
                pass

        async def receive_from_assemblyai():
            try:
                async for msg in assembly_ws:
                    msg_json = json.loads(msg)

                    # Handle transcription text
                    if "text" in msg_json and msg_json["text"].strip() != "":
                        await websocket.send_json({
                            "type": "transcript",
                            "text": msg_json["text"],
                            "is_final": msg_json.get("message_type") == "FinalTranscript"
                        })

                    # Handle turn end signal
                    if msg_json.get("message_type") == "TurnEnd":
                        await websocket.send_json({"type": "end_of_turn"})
            except Exception:
                pass

        # Run both tasks concurrently
        await asyncio.gather(receive_from_client(), receive_from_assemblyai())

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
