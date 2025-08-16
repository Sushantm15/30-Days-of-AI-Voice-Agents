from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import logging

from app.schemas import TextRequest, LLMResponse
from app.services.stt import speech_to_text
from app.services.tts import text_to_speech
from app.services.llm import query_llm
from app.utils.logger import get_logger

from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MURF_API_KEY = os.getenv("MURF_API_KEY")

# Create FastAPI app
app = FastAPI(title="AI Voice Agent")

# Attach logger
logger = get_logger(__name__)

# CORS middleware (frontend -> backend calls)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # you can restrict this to ["http://localhost:5500"] etc.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Only serve static files under /static
app.mount("/static", StaticFiles(directory="app/static", html=True), name="static")

def root():
    return {"message": "✅ AI Voice Agent is running!"}

# --- STT Endpoint ---
@app.post("/stt")
async def stt_endpoint(file: UploadFile = File(...)):
    try:
        text = await speech_to_text(file)
        logger.info(f"STT processed: {text}")
        return {"text": text}
    except Exception as e:
        logger.error(f"STT error: {str(e)}")
        raise HTTPException(status_code=500, detail="Speech-to-Text failed")


# --- TTS Endpoint ---
@app.post("/tts")
async def tts_endpoint(request: TextRequest):
    try:
        audio_file = text_to_speech(request.text)
        logger.info("TTS processed")
        return FileResponse(audio_file, media_type="audio/mp3", filename="output.mp3")
    except Exception as e:
        logger.error(f"TTS error: {str(e)}")
        raise HTTPException(status_code=500, detail="Text-to-Speech failed")


# --- LLM Endpoint ---
@app.post("/llm/query", response_model=LLMResponse)
async def llm_endpoint(request: TextRequest):
    try:
        response_text = query_llm(request.text)
        logger.info("LLM query processed")
        return {"response": response_text}
    except Exception as e:
        logger.error(f"LLM error: {str(e)}")
        raise HTTPException(status_code=500, detail="LLM Query failed")


# --- WebSocket Endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication.
    Accepts connections and sends back a response.
    """
    await websocket.accept()
    logger.info(f"✅ WebSocket connection established from: {websocket.client}")

    try:
        while True:
            # Wait for a message from the client
            data = await websocket.receive_text()
            logger.info(f"📩 Received WebSocket message: {data}")

            # Send back a different response (not just echo)
            response_message = f"🔊 Server received your message: '{data.upper()}'"
            await websocket.send_text(response_message)
            logger.info(f"Sent WebSocket response: {response_message}")

    except WebSocketDisconnect:
        logger.info(f" WebSocket client disconnected: {websocket.client}")

    except Exception as e:
        logger.error(f" WebSocket error: {str(e)}")
        try:
            await websocket.close()
        except Exception:
            logger.warning("WebSocket already closed.")
