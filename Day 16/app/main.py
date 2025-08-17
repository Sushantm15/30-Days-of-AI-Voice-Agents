from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import wave
import logging

app = FastAPI(title="AI Voice Agent")

# Day16:Audio Streming
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CORS (keep for client → server calls) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Root endpoint ---
@app.get("/")
def root():
    return {"message": "✅ AI Voice Agent is running (Day 16: Audio Streaming)"}


# --- WebSocket Endpoint for Audio Streaming ---
@app.websocket("/ws/audio")
async def websocket_audio(websocket: WebSocket):
    await websocket.accept()
    filename = "streamed_audio.wav"

    wf = wave.open(filename, "wb")
    wf.setnchannels(1)     
    wf.setsampwidth(2)      
    wf.setframerate(44100)  

    try:
        while True:
            data = await websocket.receive_bytes()
            wf.writeframes(data)
            logger.info(f"📩 Received audio chunk ({len(data)} bytes)")
    except WebSocketDisconnect:
        logger.info("❌ WebSocket disconnected")
    finally:
        wf.close()


# --- Day 1–5 Endpoints (commented out) ---
"""
# --- STT Endpoint ---
@app.post("/stt")
async def stt_endpoint(file: UploadFile = File(...)):
    text = await speech_to_text(file)
    return {"text": text}

# --- TTS Endpoint ---
@app.post("/tts")
async def tts_endpoint(request: TextRequest):
    audio_file = text_to_speech(request.text)
    return FileResponse(audio_file, media_type="audio/mp3", filename="output.mp3")

# --- LLM Endpoint ---
@app.post("/llm/query", response_model=LLMResponse)
async def llm_endpoint(request: TextRequest):
    response_text = query_llm(request.text)
    return {"response": response_text}

# --- WebSocket Text Endpoint (Day 5) ---
@app.websocket("/ws")
async def websocket_text(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo: {data}")
"""
