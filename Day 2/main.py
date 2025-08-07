from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Murf API key from environment variable
MURF_API_KEY = os.getenv("MURF_API_KEY")

# Define FastAPI app
app = FastAPI()

# Define input data format
class TextPayload(BaseModel):
    text: str

# Root endpoint (for testing)
@app.get("/")
def read_root():
    return {
        "message": "Murf TTS API is running!."
    }

# POST endpoint to generate voice
@app.post("/generate-voice")
def generate_voice(payload: TextPayload):
    murf_url = "https://api.murf.ai/v1/speech/generate"
    
    headers = {
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json"
    }

    body = {
        "text": payload.text,
        "voice_id": "en-US-terrell"  # Use the selected voice
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
