import os
import json
import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import aiohttp
import time

# ================== CONFIG ==================
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MURF_API_KEY = os.getenv("MURF_API_KEY")
CHAT_HISTORY_FILE = "chat_history.json"

BASE_DIR = Path(__file__).parent.resolve()
INDEX_HTML = BASE_DIR / "index.html"

# ================== APP ==================
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Serve frontend
@app.get("/")
async def index():
    if INDEX_HTML.exists():
        return FileResponse(str(INDEX_HTML))
    return HTMLResponse("<h1>index.html not found</h1>", status_code=404)

# ================== HELPER FUNCTIONS ==================
def save_chat(user_text, bot_text):
    if not os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "w") as f:
            json.dump([], f)
    with open(CHAT_HISTORY_FILE, "r+") as f:
        data = json.load(f)
        data.append({"user": user_text, "bot": bot_text})
        f.seek(0)
        json.dump(data, f, indent=4)

async def transcribe_audio(audio_file):
    """Upload audio to AssemblyAI and return transcript"""
    upload_url = "https://api.assemblyai.com/v2/upload"
    headers = {"authorization": ASSEMBLYAI_API_KEY}
    with open(audio_file, "rb") as f:
        async with aiohttp.ClientSession() as session:
            async with session.post(upload_url, headers=headers, data=f) as resp:
                res = await resp.json()
    audio_url = res["upload_url"]

    transcript_endpoint = "https://api.assemblyai.com/v2/transcript"
    json_data = {"audio_url": audio_url}
    async with aiohttp.ClientSession() as session:
        async with session.post(transcript_endpoint, headers=headers, json=json_data) as resp:
            transcript_res = await resp.json()
    transcript_id = transcript_res["id"]

    # Poll for completion
    while True:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{transcript_endpoint}/{transcript_id}", headers=headers) as resp:
                status_res = await resp.json()
        if status_res["status"] == "completed":
            return status_res["text"]
        elif status_res["status"] == "failed":
            return "Transcription failed"
        await asyncio.sleep(2)

async def get_llm_response(prompt):
    """Get response from LLM (OpenAI GPT-4)"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "gpt-4", "messages": [{"role": "user", "content": prompt}]}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as resp:
            res = await resp.json()
    return res["choices"][0]["message"]["content"]

async def murf_tts(text):
    """Send text to Murf API for TTS"""
    url = "https://api.murf.ai/v1/speech"
    headers = {"Authorization": f"Bearer {MURF_API_KEY}", "Content-Type": "application/json"}
    payload = {"voiceId": "en-US-Emily", "text": text, "format": "mp3"}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            res = await resp.json()
    return res.get("audioUrl")

# ================== WEBSOCKET ==================
@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("✅ WebSocket connected")

    audio_chunks = []
    chunk_counter = 0

    while True:
        try:
            data = await websocket.receive_bytes()
            audio_chunks.append(data)
            chunk_counter += 1

            # Print limited logs (every 10 chunks)
            if chunk_counter % 10 == 0:
                print(f"[Audio Chunks Received] {chunk_counter} chunks")

            # Send partial transcription every 50 chunks
            if chunk_counter % 50 == 0:
                temp_file = "temp_partial.wav"
                with open(temp_file, "wb") as f:
                    for chunk in audio_chunks:
                        f.write(chunk)
                transcript = await transcribe_audio(temp_file)
                short_transcript = transcript[:100] + ("..." if len(transcript) > 100 else "")
                await websocket.send_json({"type": "partial_transcript", "text": short_transcript})
                print(f"[Partial Transcript] {short_transcript}")

            # If "END" marker is sent, finalize
            if data == b"END":
                final_file = "temp_final.wav"
                with open(final_file, "wb") as f:
                    for chunk in audio_chunks[:-1]:  # exclude END
                        f.write(chunk)
                transcript = await transcribe_audio(final_file)
                llm_response = await get_llm_response(transcript)
                audio_url = await murf_tts(llm_response)

                # Save chat
                save_chat(transcript, llm_response)

                # Send final results
                await websocket.send_json({
                    "type": "final",
                    "transcript": transcript,
                    "response": llm_response,
                    "audio_url": audio_url
                })
                print(f"[Final Transcript] {transcript[:100]}...")
                print(f"[AI Response] {llm_response[:100]}...")
                audio_chunks.clear()
                chunk_counter = 0

        except Exception as e:
            print(f"❌ Error in websocket: {e}")
            break
