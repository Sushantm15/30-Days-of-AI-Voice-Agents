from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv
from pathlib import Path
import shutil
import assemblyai as aai
import time
import base64
import asyncio
from typing import Optional

# Load .env variables
load_dotenv()
MURF_API_KEY = os.getenv("MURF_API_KEY")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

# Initialize AssemblyAI transcriber
aai.settings.api_key = ASSEMBLYAI_API_KEY
transcriber = aai.Transcriber()

app = FastAPI()

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from /uploads
uploads_dir = Path("uploads")
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Text model for TTS
class TextPayload(BaseModel):
    text: str

@app.get("/")
def read_root():
    return {"message": "Murf TTS API is running!"}

@app.post("/generate-voice")
def generate_voice(payload: TextPayload):
    murf_url = "https://api.murf.ai/v1/speech/generate"
    headers = {
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json"
    }
    body = {
        "text": payload.text,
        "voice_id": "en-US-terrell"
    }

    response = requests.post(murf_url, headers=headers, json=body)

    if response.status_code == 200:
        return {
            "message": "Voice generated successfully",
            "data": response.json()
        }
    else:
        return {
            "error": "Failed to generate audio",
            "status_code": response.status_code,
            "details": response.json()
        }

@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    file_path = uploads_dir / file.filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size_kb": round(file_path.stat().st_size / 1024, 2)
    }

# ✅ NEW ENDPOINT for transcription
@app.post("/transcribe/file")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        audio_bytes = await file.read()
        transcript = transcriber.transcribe(audio_bytes)
        return {
            "status": "success",
            "transcription": transcript.text
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# -------------------
# NEW /tts/echo endpoint combining transcription + Murf voice generation + saving audio locally and returning URL
# -------------------

def generate_murf_audio_sync(text: str, voice_id: Optional[str] = "en-US-terrell") -> dict:
    murf_url = "https://api.murf.ai/v1/speech/generate"
    headers = {
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json"
    }
    body = {
        "text": text,
        "voice_id": voice_id
    }
    response = requests.post(murf_url, headers=headers, json=body)
    response.raise_for_status()
    return response.json()

@app.post("/tts/echo")
async def echo_tts(file: UploadFile = File(...)):
    try:
        audio_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unable to read uploaded file: {e}")

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Run transcription (blocking) in threadpool
    loop = asyncio.get_running_loop()
    try:
        transcript_result = await loop.run_in_executor(None, transcriber.transcribe, audio_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

    text = transcript_result.text.strip()
    if not text:
        return {"status": "error", "message": "No text found in transcription", "transcription": ""}

    # Call Murf API in threadpool (blocking)
    try:
        murf_resp_json = await loop.run_in_executor(None, generate_murf_audio_sync, text, "en-US-terrell")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Murf generation failed: {e}")

    # Extract audio URL or base64 audio
    audio_url = murf_resp_json.get("audio_url") or murf_resp_json.get("audioFile")

    filename = f"murf_echo_{int(time.time())}.mp3"
    save_path = uploads_dir / filename

    try:
        if audio_url:
            r = requests.get(audio_url, stream=True)
            r.raise_for_status()
            with open(save_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        else:
            # try base64 audio
            b64_audio = murf_resp_json.get("audio") or murf_resp_json.get("audio_base64")
            if not b64_audio:
                raise Exception("Murf response doesn't contain audio_url, audioFile, or base64 audio")
            if b64_audio.startswith("data:"):
                b64_audio = b64_audio.split(",", 1)[1]
            audio_data = base64.b64decode(b64_audio)
            with open(save_path, "wb") as f:
                f.write(audio_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to obtain/save Murf audio: {e}")

    return {
        "status": "success",
        "transcription": text,
        "audio_url": f"/uploads/{filename}"
    }
