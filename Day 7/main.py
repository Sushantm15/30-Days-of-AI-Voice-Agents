from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from pathlib import Path
import requests
import os
import time

# Load environment variables
load_dotenv()
MURF_API_KEY = os.getenv("MURF_API_KEY")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

if not ASSEMBLYAI_API_KEY:
    raise RuntimeError("Missing ASSEMBLYAI_API_KEY in environment")
if not MURF_API_KEY:
    raise RuntimeError("Missing MURF_API_KEY in environment")

uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


class AssemblyTranscriber:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.upload_url = "https://api.assemblyai.com/v2/upload"
        self.transcript_url = "https://api.assemblyai.com/v2/transcript"

    def upload_audio(self, audio_bytes: bytes) -> str:
        headers = {"authorization": self.api_key}
        response = requests.post(self.upload_url, headers=headers, data=audio_bytes)
        response.raise_for_status()
        return response.json()["upload_url"]

    def request_transcription(self, audio_url: str) -> str:
        headers = {"authorization": self.api_key, "content-type": "application/json"}
        payload = {"audio_url": audio_url}
        response = requests.post(self.transcript_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["id"]

    def get_transcription_result(self, transcript_id: str, poll_interval: float = 1.0) -> dict:
        headers = {"authorization": self.api_key}
        while True:
            response = requests.get(f"{self.transcript_url}/{transcript_id}", headers=headers)
            response.raise_for_status()
            result = response.json()
            status = result.get("status")
            if status == "completed":
                return result
            if status == "failed":
                raise Exception("Transcription failed: " + str(result))
            time.sleep(poll_interval)

    def transcribe(self, audio_bytes: bytes) -> dict:
        audio_url = self.upload_audio(audio_bytes)
        transcript_id = self.request_transcription(audio_url)
        return self.get_transcription_result(transcript_id)


transcriber = AssemblyTranscriber(ASSEMBLYAI_API_KEY)


@app.post("/tts/echo")
async def echo_bot_v20(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No audio file provided")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        transcript_result = transcriber.transcribe(audio_bytes)
        text = transcript_result.get("text", "").strip()
        if not text:
            return JSONResponse(status_code=400, content={"error": "No text found in transcription"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

    murf_payload = {
        "text": text,
        "voice_id": "en-US-terrell" 
    }

    murf_headers = {
        "Content-Type": "application/json",
        "api-key": MURF_API_KEY
    }

    try:
        murf_response = requests.post(
            "https://api.murf.ai/v1/speech/generate",
            headers=murf_headers,
            json=murf_payload
        )
        murf_response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Murf TTS request failed: {e}")

    murf_json = murf_response.json()
    audio_url = murf_json.get('audioFile') or murf_json.get('audio_url')

    if not audio_url:
        raise HTTPException(status_code=500, detail="Murf response missing audio URL")

    # Save audio locally in uploads folder
    try:
        filename = f"murf_echo_{int(time.time())}.mp3"
        save_path = uploads_dir / filename

        audio_resp = requests.get(audio_url, stream=True)
        audio_resp.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in audio_resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        # Return URL for frontend to fetch audio
        return {
            "status": "success",
            "transcription": text,
            "audio_url": f"/uploads/{filename}"
        }

    except Exception as e:
        # If saving fails, return the direct Murf URL anyway
        return {
            "status": "success",
            "transcription": text,
            "audio_url": audio_url,
            "warning": f"Could not save audio locally: {str(e)}"
        }


@app.get("/")
async def root():
    return {"status": "ok", "message": "TTS Echo FastAPI server running"}
