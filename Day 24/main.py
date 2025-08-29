import os
import json
import asyncio
import time
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

import aiohttp
from dotenv import load_dotenv

# ================== CONFIG / ENV ==================
BASE_DIR = Path(__file__).parent.resolve()
INDEX_HTML = BASE_DIR / "index.html"
CHAT_HISTORY_FILE = BASE_DIR / "chat_history.json"

load_dotenv()
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY", "")
MURF_API_KEY       = os.getenv("MURF_API_KEY", "")
MURF_VOICE_ID      = os.getenv("MURF_VOICE_ID", "en-US-Emily")  # fallback
OPENAI_MODEL       = os.getenv("OPENAI_MODEL", "gpt-4o-mini")   # light/fast; change if needed

REQUIRED = {
    "ASSEMBLYAI_API_KEY": ASSEMBLYAI_API_KEY,
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "MURF_API_KEY": MURF_API_KEY,
}
missing = [k for k, v in REQUIRED.items() if not v]
if missing:
    raise RuntimeError(f"Missing required env keys: {', '.join(missing)}")

# ================== APP ==================
app = FastAPI(title="Day 24 Persona Voice Agent")

# CORS (note: CORS middleware does not affect WS origin checks in Starlette —
# we simply accept the socket below, so 403s from origin are avoided)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
    allow_credentials=True
)

# ================== ROUTES ==================
@app.get("/")
async def index():
    if INDEX_HTML.exists():
        return FileResponse(str(INDEX_HTML))
    return HTMLResponse("<h1>index.html not found</h1>", status_code=404)

# ================== HELPERS ==================
def truncate(s: str, n: int = 120) -> str:
    s = s or ""
    return (s[:n] + "…") if len(s) > n else s

def ensure_history_file():
    if not CHAT_HISTORY_FILE.exists():
        CHAT_HISTORY_FILE.write_text("[]", encoding="utf-8")

def save_chat(user_text: str, bot_text: str, persona: str):
    ensure_history_file()
    try:
        data = json.loads(CHAT_HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = []
    data.append({"persona": persona, "user": user_text, "bot": bot_text})
    CHAT_HISTORY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def persona_to_system_prompt(persona: str) -> str:
    persona = (persona or "Default").strip()
    if persona.lower() == "pirate":
        return (
            "You are a friendly pirate. Speak like a pirate (yo-ho, matey), "
            "but keep answers helpful and concise."
        )
    if persona.lower() == "cowboy":
        return (
            "You are a warm cowboy from the Old West. Use casual, friendly cowboy slang, "
            "stay helpful and concise."
        )
    if persona.lower() == "robot":
        return (
            "You are a precise, slightly monotone robot. Use brief, structured sentences; "
            "be efficient and helpful."
        )
    if persona.lower() == "comedian":
        return (
            "You are a playful comedian. Keep answers helpful, add light humor where appropriate "
            "(no offensive jokes), stay concise."
        )
    if persona.lower() == "teacher":
        return (
            "You are a clear, encouraging teacher. Explain concepts step-by-step, "
            "use simple language, and be concise."
        )
    # Default
    return "You are a helpful, concise AI voice assistant."

async def assemblyai_transcribe_from_file(file_path: Path) -> str:
    """
    Uploads an audio file to AssemblyAI and returns the transcript text.
    Supports WebM/Opus (what the browser records).
    """
    headers = {"authorization": ASSEMBLYAI_API_KEY}
    upload_url = "https://api.assemblyai.com/v2/upload"

    # 1) Upload
    async with aiohttp.ClientSession() as session:
        with file_path.open("rb") as f:
            async with session.post(upload_url, headers=headers, data=f) as r:
                up = await r.json()
    audio_url = up["upload_url"]

    # 2) Create transcription job
    transcript_url = "https://api.assemblyai.com/v2/transcript"
    payload = {"audio_url": audio_url}
    async with aiohttp.ClientSession() as session:
        async with session.post(transcript_url, headers=headers, json=payload) as r:
            job = await r.json()
    tid = job["id"]

    # 3) Poll
    while True:
        await asyncio.sleep(2)
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{transcript_url}/{tid}", headers=headers) as r:
                status = await r.json()
        if status.get("status") == "completed":
            return status.get("text", "")
        if status.get("status") == "failed":
            return "Transcription failed"

async def openai_chat(system_prompt: str, user_text: str) -> str:
    """
    Simple non-streaming OpenAI chat call. You can switch OPENAI_MODEL in .env.
    """
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as resp:
            res = await resp.json()
    return res["choices"][0]["message"]["content"]

async def murf_tts(text: str, voice_id: Optional[str] = None) -> Optional[str]:
    """
    Murf REST TTS (non-streaming). Returns an audioUrl that the frontend can play.
    """
    voice_id = voice_id or MURF_VOICE_ID
    url = "https://api.murf.ai/v1/speech"
    headers = {"Authorization": f"Bearer {MURF_API_KEY}", "Content-Type": "application/json"}
    payload = {"voiceId": voice_id, "text": text, "format": "mp3"}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            res = await resp.json()
    return res.get("audioUrl")

# ================== WEBSOCKET ==================
@app.websocket("/ws/llm-murf")
async def ws_endpoint(websocket: WebSocket):
    # Accept immediately to avoid 403s on some browsers/origins.
    await websocket.accept()
    print("✅ WS connected")

    # Session state
    persona = "Default"
    chunks: List[bytes] = []
    chunk_count = 0

    # temp file per connection
    tmp_file = BASE_DIR / f"rec_{int(time.time()*1000)}.webm"

    try:
        while True:
            message = await websocket.receive()

            # Text messages (config/control)
            if "text" in message and message["text"] is not None:
                txt = message["text"].strip()
                # Try parse JSON control first
                try:
                    obj = json.loads(txt)
                    # persona update
                    if obj.get("type") == "config" and "persona" in obj:
                        persona = obj["persona"] or "Default"
                        await websocket.send_json({"type": "info", "msg": f"persona_set:{persona}"})
                        print(f"👤 Persona set -> {persona}")
                        continue
                    # explicit EOF
                    if obj.get("type") == "eof":
                        print("📩 EOF received (JSON). Processing…")
                        # finalize & process
                        if chunks:
                            tmp_file.write_bytes(b"".join(chunks))
                        await handle_pipeline(websocket, tmp_file, persona)
                        # reset
                        chunks.clear()
                        chunk_count = 0
                        continue
                except Exception:
                    # If not JSON, check for legacy "END" marker
                    if txt.upper() == "END":
                        print("📩 EOF received (text END). Processing…")
                        if chunks:
                            tmp_file.write_bytes(b"".join(chunks))
                        await handle_pipeline(websocket, tmp_file, persona)
                        chunks.clear()
                        chunk_count = 0
                        continue
                # Unknown text -> ignore or log lightly
                continue

            # Binary messages (audio chunks)
            if "bytes" in message and message["bytes"] is not None:
                data: bytes = message["bytes"]

                # Legacy binary END marker
                if data == b"END":
                    print("📩 EOF received (binary END). Processing…")
                    if chunks:
                        tmp_file.write_bytes(b"".join(chunks))
                    await handle_pipeline(websocket, tmp_file, persona)
                    chunks.clear()
                    chunk_count = 0
                    continue

                # Accumulate chunk
                chunks.append(data)
                chunk_count += 1

                # Limited logging (every 10 chunks)
                if (chunk_count % 10) == 0:
                    print(f"[Audio] received {chunk_count} chunks")

                # Optional: send heartbeat to UI
                if (chunk_count % 25) == 0:
                    await websocket.send_json({"type": "progress", "chunks": chunk_count})

            else:
                # unexpected frame
                print("⚠️ Unknown WS frame:", message)

    except Exception as e:
        print(f"❌ WS error: {e}")
    finally:
        try:
            if tmp_file.exists():
                tmp_file.unlink(missing_ok=True)
        except Exception:
            pass
        await websocket.close()
        print("🔌 WS closed")

# ---------- Pipeline (STT -> LLM -> TTS -> send UI) ----------
async def handle_pipeline(ws: WebSocket, file_path: Path, persona: str):
    try:
        # 1) STT
        transcript = await assemblyai_transcribe_from_file(file_path)
        short_t = truncate(transcript)
        print(f"[Transcript] {short_t}")
        await ws.send_json({"type": "transcript", "text": transcript})

        # 2) LLM (persona)
        sys_prompt = persona_to_system_prompt(persona)
        reply = await openai_chat(sys_prompt, transcript)
        short_r = truncate(reply)
        print(f"[LLM] {short_r}")
        await ws.send_json({"type": "ai_response", "text": reply})

        # 3) TTS
        audio_url = await murf_tts(reply, voice_id=MURF_VOICE_ID)
        if audio_url:
            await ws.send_json({"type": "audio_url", "url": audio_url})
        else:
            await ws.send_json({"type": "audio_error", "msg": "No audioUrl from TTS"})

        # 4) Save chat
        save_chat(transcript, reply, persona)

        # 5) Signal done
        await ws.send_json({"type": "final"})
    except Exception as e:
        print(f"❌ Pipeline error: {e}")
        try:
            await ws.send_json({"type": "error", "msg": str(e)})
        except Exception:
            pass

# ================== RUN ==================
if __name__ == "__main__":
    import uvicorn
    # Run with: python main.py
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
