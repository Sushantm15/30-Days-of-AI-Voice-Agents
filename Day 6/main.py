#file is added after downloading from the web in uploads
from fastapi import FastAPI, UploadFile, File
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
