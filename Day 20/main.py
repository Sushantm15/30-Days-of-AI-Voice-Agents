import os
import asyncio
import json
import websockets
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv()
MURF_API_KEY = os.getenv("MURF_API_KEY")
MURF_WS_URL = (
    f"wss://api.murf.ai/v1/speech/stream-input?api-key={MURF_API_KEY}"
    f"&sample_rate=44100&channel_type=MONO&format=WAV"
)

# Create FastAPI app
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve index.html
@app.get("/")
async def index():
    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content, status_code=200)

# Simulated LLM streaming generator
async def stream_llm_response():
    responses = ["Hello,", " this is a streaming", " LLM response.", " Enjoy!"]
    for chunk in responses:
        await asyncio.sleep(0.5)
        yield chunk

# Send LLM chunk to Murf and receive base64 audio
async def send_to_murf_and_get_audio(llm_chunk):
    try:
        async with websockets.connect(MURF_WS_URL) as ws:
            await ws.send(json.dumps({"text": llm_chunk}))
            response = await ws.recv()
            data = json.loads(response)
            return data.get("audio_base64")
    except Exception as e:
        print("Error sending to Murf:", e)
        return None

# WebSocket endpoint
@app.websocket("/ws/llm-murf")
async def llm_murf_ws(websocket: WebSocket):
    await websocket.accept()
    print("Client connected.")
    audio_chunks = []  # Array to accumulate base64 chunks

    try:
        # Task to stream LLM to Murf
        async def llm_to_murf():
            async for llm_chunk in stream_llm_response():
                audio_base64 = await send_to_murf_and_get_audio(llm_chunk)
                if audio_base64:
                    audio_chunks.append(audio_base64)  # accumulate
                    await websocket.send_json({"audio_chunk": audio_base64})
                    print("Sent audio chunk to client:", audio_base64[:60], "...")

        # Task to receive audio from client
        async def receive_client_audio():
            while True:
                data = await websocket.receive_bytes()
                print("Received audio buffer from client:", len(data))

        # Run both tasks concurrently
        await asyncio.gather(llm_to_murf(), receive_client_audio())

    except Exception as e:
        print("WebSocket error:", e)
    finally:
        await websocket.close()
        print("Client disconnected.")

# Entry point
if __name__ == "__main__":
    uvicorn.run("main:app",
                host="0.0.0.0",
                port=8000,
                reload=True)
