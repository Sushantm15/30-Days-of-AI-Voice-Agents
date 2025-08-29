import os
import json
import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import aiohttp
import time
import threading
from typing import Dict, Any, Generator

# ========== CONFIG ==========
ASSEMBLYAI_API_KEY = "your_assemblyai_api_key"
OPENAI_API_KEY = "your_openai_api_key"
MURF_API_KEY = "your_murf_api_key"
CHAT_HISTORY_FILE = "chat_history.json"

CHUNK_LIMIT = 10  # Process every 10 audio chunks for early transcription

# New: stream safety limits and debug toggles
MAX_TTS_STREAM_BYTES = int(os.getenv("MAX_TTS_STREAM_BYTES", 5 * 1024 * 1024))  # default 5MB
MAX_TTS_STREAM_SECONDS = int(os.getenv("MAX_TTS_STREAM_SECONDS", 30))  # default 30s
ENABLE_DEBUG_TIMING = os.getenv("ENABLE_DEBUG_TIMING", "1") != "0"

# Create FastAPI app
app = FastAPI()

# Serve index.html
@app.get("/")
async def get_index():
    with open("index.html", "r") as f:
        return HTMLResponse(content=f.read(), status_code=200)

# =================== WebSocket for Voice Agent ===================
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("✅ WebSocket connection established")

    if not os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "w") as f:
            json.dump([], f)

    audio_buffer = []

    while True:
        try:
            data = await websocket.receive_bytes()  # Receive binary audio

            audio_buffer.append(data)

            # Process early if we reached CHUNK_LIMIT
            if len(audio_buffer) >= CHUNK_LIMIT:
                partial_file = "partial_audio.wav"
                with open(partial_file, "wb") as f:
                    for chunk in audio_buffer:
                        f.write(chunk)
                print(f"🔊 Processed {len(audio_buffer)} audio chunks")  # limited CMD log
                audio_buffer.clear()

                transcript = await transcribe_audio(partial_file)
                if transcript:
                    print(f"📝 Transcript: {transcript[:100]}...")  # first 100 chars only
                    await websocket.send_json({"type": "transcript", "text": transcript})

                    llm_response = await get_llm_response(transcript)
                    print(f"🤖 LLM Response: {llm_response[:100]}...")
                    await websocket.send_json({"type": "ai_response", "text": llm_response})

                    audio_url = await murf_text_to_speech(llm_response)
                    if audio_url:
                        await websocket.send_json({"type": "audio_chunk", "audio_url": audio_url})

        except Exception as e:
            print(f"❌ WebSocket error: {e}")
            break

# ================== Helper Functions ==================
async def transcribe_audio(audio_file):
    """Send audio to AssemblyAI for transcription"""
    upload_url = "https://api.assemblyai.com/v2/upload"
    headers = {"authorization": ASSEMBLYAI_API_KEY}

    with open(audio_file, "rb") as f:
        async with aiohttp.ClientSession() as session:
            async with session.post(upload_url, headers=headers, data=f) as resp:
                res = await resp.json()
                audio_url = res.get("upload_url")

    transcript_endpoint = "https://api.assemblyai.com/v2/transcript"
    json_data = {"audio_url": audio_url}
    async with aiohttp.ClientSession() as session:
        async with session.post(transcript_endpoint, headers=headers, json=json_data) as resp:
            res = await resp.json()
            transcript_id = res.get("id")

    # Poll until transcription done
    while True:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{transcript_endpoint}/{transcript_id}", headers=headers) as resp:
                result = await resp.json()
                status = result.get("status")
                if status == "completed":
                    return result.get("text")
                elif status == "failed":
                    return "Transcription failed"
        await asyncio.sleep(2)

async def get_llm_response(prompt):
    """Send prompt to OpenAI GPT-4 for response"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": prompt}]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as resp:
            res = await resp.json()
            return res["choices"][0]["message"]["content"]

async def murf_text_to_speech(text):
    """Convert text to speech using Murf API"""
    url = "https://api.murf.ai/v1/speech"
    headers = {
        "Authorization": f"Bearer {MURF_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "voiceId": "en-US-Emily",
        "text": text,
        "format": "mp3"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            res = await resp.json()
            return res.get("audioUrl")

def save_chat_history(user_text, bot_response):
    """Save chat history locally"""
    if not os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "w") as f:
            json.dump([], f)
    with open(CHAT_HISTORY_FILE, "r+") as f:
        data = json.load(f)
        data.append({"user": user_text, "bot": bot_response})
        f.seek(0)
        json.dump(data, f, indent=4)

def send_to_murf_stream(text: str) -> Generator[bytes, None, None]:
    """
    Send text to Murf TTS and stream back the audio bytes.
    Safety: stop after MAX_TTS_STREAM_BYTES or MAX_TTS_STREAM_SECONDS.
    """
    headers = {
        "Authorization": f"Bearer {MURF_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",  # or audio/wav depending on Murf
    }
    payload = {
        "voice": "en-US-Emily",
        "input": text,
        "format": "mp3"
    }

    # Defensive: if no text, yield nothing (caller will handle JSON response)
    if not text or text.strip() == "":
        if ENABLE_DEBUG_TIMING:
            print("send_to_murf_stream: empty assistant text, skipping TTS.")
        return
        yield  # generator sentinel (never reached)

    start_time = time.time()
    total_bytes = 0
    timeout = (10, 60)  # (connect_timeout, read_timeout) adjust as needed

    try:
        with requests.post(MURF_TTS_ENDPOINT, json=payload, headers=headers, stream=True, timeout=timeout) as r:
            r.raise_for_status()
            # Iterate with a moderate chunk size; stop if limits exceeded.
            for chunk in r.iter_content(chunk_size=4096):
                if chunk:
                    total_bytes += len(chunk)
                    yield chunk
                    # Stop if exceeded bytes or time limits
                    elapsed = time.time() - start_time
                    if total_bytes >= MAX_TTS_STREAM_BYTES:
                        print(f"send_to_murf_stream: reached MAX_TTS_STREAM_BYTES ({total_bytes} bytes); stopping stream.")
                        break
                    if elapsed >= MAX_TTS_STREAM_SECONDS:
                        print(f"send_to_murf_stream: reached MAX_TTS_STREAM_SECONDS ({elapsed:.1f}s); stopping stream.")
                        break
    except requests.HTTPError as e:
        # propagate to caller via exception, caller will send a JSON error chunk
        raise
    except Exception as e:
        # log unexpected errors
        print(f"send_to_murf_stream: unexpected error: {e}")
        raise

# ================== Run App ==================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
