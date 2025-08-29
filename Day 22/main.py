import os
import json
import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import aiohttp
import time

# ========== CONFIG ==========
ASSEMBLYAI_API_KEY = "your_assemblyai_api_key"
OPENAI_API_KEY = "your_openai_api_key"
MURF_API_KEY = "your_murf_api_key"
CHAT_HISTORY_FILE = "chat_history.json"

CHUNK_LIMIT = 10  # Process every 10 audio chunks for early transcription
CHUNK_BATCH_SIZE = 5  # Number of chunks to process in each batch

# ========== FastAPI ==========
app = FastAPI()

@app.get("/")
async def get_index():
    with open("index.html", "r") as f:
        return HTMLResponse(content=f.read(), status_code=200)

# ========== WebSocket ==========
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("✅ WebSocket connected")
    if not os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "w") as f:
            json.dump([], f)

    audio_chunks = []
    batch_index = 0  # track batches per websocket connection

    # helper to spawn background processing tasks
    async def process_audio_batch(websocket: WebSocket, chunks: list, final: bool, batch_idx: int):
        """
        Write chunks to a temp file, transcribe, get LLM response, call Murf TTS,
        and send a JSON payload back via websocket. 'final' indicates final batch.
        """
        try:
            fname = f"temp_audio_{int(time.time()*1000)}.wav"
            with open(fname, "wb") as f:
                f.write(b"".join(chunks))
            # transcribe
            transcript = await transcribe_audio(fname)
            print(f"📝 (batch {batch_idx}{' final' if final else ' partial'}) Transcript: {transcript}")

            # LLM
            response_text = await get_llm_response(transcript)
            print(f"🤖 (batch {batch_idx}{' final' if final else ' partial'}) LLM Response: {response_text}")

            # Save history only for final batches to avoid clutter
            if final:
                save_chat_history(transcript, response_text)

            # Murf TTS
            audio_url = await murf_text_to_speech(response_text)

            # send payload; include 'final' and 'partial' flags and batch index
            await websocket.send_json({
                "batch_index": batch_idx,
                "transcript": transcript,
                "response": response_text,
                "audio_url": audio_url,
                "partial": not bool(final),
                "final": bool(final)
            })
        except Exception as e:
            print(f"❌ Error processing audio batch: {e}")
            try:
                await websocket.send_json({"error": "batch_processing_failed", "detail": str(e), "batch_index": batch_idx})
            except Exception:
                pass
        finally:
            # try to cleanup temp file (ignore errors)
            try:
                os.remove(fname)
            except Exception:
                pass

    while True:
        try:
            # Receive either binary or text frames
            msg = await websocket.receive()
            # websocket.receive() returns dict with 'type' and 'bytes'/'text'
            if msg.get("type") == "websocket.disconnect":
                print("WebSocket disconnected")
                break

            # Binary audio chunk
            if msg.get("bytes"):
                chunk = msg["bytes"]
                # Treat a textual END sent as bytes too
                if chunk == b"END":
                    print("✅ Received END signal (bytes). Processing remaining audio as final...")
                    # If there are pending chunks, process them as final (await to ensure finality)
                    if audio_chunks:
                        batch = audio_chunks.copy()
                        audio_chunks.clear()
                        batch_index += 1
                        await process_audio_batch(websocket, batch, final=True, batch_idx=batch_index)
                    else:
                        # still send an empty final message if needed
                        batch_index += 1
                        await websocket.send_json({"batch_index": batch_index, "transcript": "", "response": "", "audio_url": None, "partial": False, "final": True})
                else:
                    audio_chunks.append(chunk)
                    # If we've collected enough chunks, process them early in background
                    if len(audio_chunks) >= CHUNK_BATCH_SIZE:
                        batch = audio_chunks.copy()
                        audio_chunks.clear()
                        batch_index += 1
                        # spawn background task so we keep receiving further chunks
                        asyncio.create_task(process_audio_batch(websocket, batch, final=False, batch_idx=batch_index))

            # Text frame (e.g., client sends "END" as text)
            elif msg.get("text") is not None:
                text_msg = msg["text"]
                if text_msg.strip().upper() == "END":
                    print("✅ Received END signal (text). Processing remaining audio as final...")
                    if audio_chunks:
                        batch = audio_chunks.copy()
                        audio_chunks.clear()
                        batch_index += 1
                        await process_audio_batch(websocket, batch, final=True, batch_idx=batch_index)
                    else:
                        batch_index += 1
                        await websocket.send_json({"batch_index": batch_index, "transcript": "", "response": "", "audio_url": None, "partial": False, "final": True})
                else:
                    # If client sends other text frames, ignore or log
                    print(f"Received text frame (ignored): {text_msg}")

        except Exception as e:
            print(f"❌ Error in websocket loop: {e}")
            break

# ========== Helper Functions ==========
async def transcribe_audio(audio_file):
    """Send audio to AssemblyAI for transcription"""
    url = "https://api.assemblyai.com/v2/upload"
    headers = {"authorization": ASSEMBLYAI_API_KEY}

    # Upload audio
    async with aiohttp.ClientSession() as session:
        with open(audio_file, "rb") as f:
            async with session.post(url, headers=headers, data=f) as resp:
                upload_res = await resp.json()
    audio_url = upload_res.get("upload_url")
    if not audio_url:
        return None

    # Create transcription job
    transcript_endpoint = "https://api.assemblyai.com/v2/transcript"
    json_data = {"audio_url": audio_url}
    async with aiohttp.ClientSession() as session:
        async with session.post(transcript_endpoint, json=json_data, headers=headers) as resp:
            response = await resp.json()
    transcript_id = response.get("id")
    if not transcript_id:
        return None

    # Poll transcription until complete
    while True:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{transcript_endpoint}/{transcript_id}", headers=headers) as resp:
                result = await resp.json()
        if result.get("status") == "completed":
            return result.get("text")
        elif result.get("status") == "failed":
            return "Transcription failed"
        await asyncio.sleep(1)

async def get_llm_response(prompt):
    """Send prompt to LLM API (OpenAI)"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "gpt-4", "messages": [{"role": "user", "content": prompt}]}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as resp:
            result = await resp.json()
    return result["choices"][0]["message"]["content"]

async def murf_text_to_speech(text):
    """Convert text to speech via Murf API"""
    url = "https://api.murf.ai/v1/speech"
    headers = {"Authorization": f"Bearer {MURF_API_KEY}", "Content-Type": "application/json"}
    payload = {"voiceId": "en-US-Emily", "text": text, "format": "mp3"}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            result = await resp.json()
    return result.get("audioUrl")

def save_chat_history(user_text, bot_response):
    """Append conversation to JSON file"""
    with open(CHAT_HISTORY_FILE, "r+") as f:
        data = json.load(f)
        data.append({"user": user_text, "bot": bot_response})
        f.seek(0)
        json.dump(data, f, indent=4)

# ========== Run ==========
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
