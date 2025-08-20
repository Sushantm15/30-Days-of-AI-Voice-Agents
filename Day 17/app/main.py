import os
import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
static_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/")
async def root():
    return {"message": "Go to /static/index.html in browser"}

@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected")

    try:
        async for message in websocket.iter_text():
            # Simulate transcription delay
            await asyncio.sleep(0.5)
            # Fake transcription text
            fake_text = "Hello, this is AI."
            await websocket.send_text(fake_text)
    except Exception as e:
        print("WebSocket error:", e)

    print("Connection closed")
