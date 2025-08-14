from fastapi import FastAPI, UploadFile, File, HTTPException, Form
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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not ASSEMBLYAI_API_KEY:
    raise RuntimeError("Missing ASSEMBLYAI_API_KEY in environment")
if not MURF_API_KEY:
    raise RuntimeError("Missing MURF_API_KEY in environment")
if not GEMINI_API_KEY:
    raise RuntimeError("Missing GEMINI_API_KEY in environment")

uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Murf voice IDs
MURF_VOICE_ECHO = "en-UK-ruby"  
MURF_VOICE_LLM = "en-UK-ruby"    


class AssemblyTranscriber:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.upload_url = "https://api.assemblyai.com/v2/upload"
        self.transcript_url = "https://api.assemblyai.com/v2/transcript"

    def upload_audio(self, audio_bytes: bytes) -> str:
        headers = {"authorization": self.api_key}
        r = requests.post(self.upload_url, headers=headers, data=audio_bytes)
        r.raise_for_status()
        return r.json()["upload_url"]

    def request_transcription(self, audio_url: str) -> str:
        headers = {"authorization": self.api_key, "content-type": "application/json"}
        payload = {"audio_url": audio_url}
        r = requests.post(self.transcript_url, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()["id"]

    def get_transcription_result(self, transcript_id: str, poll_interval: float = 1.0) -> dict:
        headers = {"authorization": self.api_key}
        while True:
            r = requests.get(f"{self.transcript_url}/{transcript_id}", headers=headers)
            r.raise_for_status()
            result = r.json()
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


def murf_tts(voice_id: str, text: str) -> str:
    """Send text to Murf and return audio URL"""
    murf_payload = {
        "voiceId": voice_id,
        "text": text,
        "format": "MP3",
        "sampleRate": 24000
    }
    murf_headers = {
        "Content-Type": "application/json",
        "api-key": MURF_API_KEY
    }
    r = requests.post("https://api.murf.ai/v1/speech/generate", headers=murf_headers, json=murf_payload)
    r.raise_for_status()
    murf_json = r.json()
    return murf_json.get("audioFile") or murf_json.get("audioUrl")


@app.post("/tts/echo")
async def echo_bot(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No audio file provided")
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Transcribe
    try:
        transcript_result = transcriber.transcribe(audio_bytes)
        text = transcript_result.get("text", "").strip()
        if not text:
            return JSONResponse(status_code=400, content={"error": "No text found in transcription"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

    # TTS
    try:
        audio_url = murf_tts(MURF_VOICE_ECHO, text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Murf TTS request failed: {e}")

    # Save locally
    filename = f"murf_echo_{int(time.time())}.mp3"
    save_path = uploads_dir / filename
    try:
        audio_resp = requests.get(audio_url, stream=True)
        audio_resp.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in audio_resp.iter_content(chunk_size=8192):
                f.write(chunk)
    except Exception:
        return {
            "status": "success",
            "transcription": text,
            "audio_url": audio_url,
            "warning": "Could not save audio locally"
        }

    return {
        "status": "success",
        "transcription": text,
        "audio_url": f"/uploads/{filename}"
    }


@app.post("/llm/query")
async def llm_query(file: UploadFile = File(None), text: str = Form(None)):
    if file:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        try:
            transcript_result = transcriber.transcribe(audio_bytes)
            user_text = transcript_result.get("text", "").strip()
            if not user_text:
                return JSONResponse(status_code=400, content={"error": "No text found in transcription"})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
    elif text:
        user_text = text.strip()
        if not user_text:
            raise HTTPException(status_code=400, detail="Missing 'text' in request body")
    else:
        raise HTTPException(status_code=400, detail="No audio or text provided")

    # Query Gemini 1.5 Flash
    gemini_payload = {
        "contents": [{"role": "user", "parts": [{"text": user_text}]}]
    }
    gemini_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(gemini_url, headers=headers, json=gemini_payload)
        resp.raise_for_status()
        data = resp.json()
        model_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        if not model_text:
            raise HTTPException(status_code=500, detail="LLM did not return a response")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Gemini API request failed: {e}")

    # Send LLM response to Murf
    try:
        audio_url = murf_tts(MURF_VOICE_LLM, model_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Murf TTS request failed: {e}")

    # Save locally
    filename = f"murf_llm_{int(time.time())}.mp3"
    save_path = uploads_dir / filename
    try:
        audio_resp = requests.get(audio_url, stream=True)
        audio_resp.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in audio_resp.iter_content(chunk_size=8192):
                f.write(chunk)
    except Exception:
        return {
            "status": "success",
            "transcription": user_text,
            "llm_response": model_text,
            "audio_url": audio_url,
            "warning": "Could not save audio locally"
        }

    return {
        "status": "success",
        "transcription": user_text,
        "llm_response": model_text,
        "audio_url": f"/uploads/{filename}"
    }


@app.get("/")
async def root():
    return {"status": "ok", "message": "TTS Echo FastAPI server running with LLM endpoint"}
