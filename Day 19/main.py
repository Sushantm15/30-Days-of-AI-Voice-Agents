import os
import asyncio
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import assemblyai as aai
import google.generativeai as genai
from assemblyai.streaming.v3 import (
    StreamingClient, StreamingClientOptions,
    StreamingParameters, StreamingSessionParameters,
    StreamingEvents, BeginEvent, TurnEvent,
    TerminationEvent, StreamingError
)

# Load API keys
load_dotenv()
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

aai.settings.api_key = ASSEMBLYAI_API_KEY
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def get_index():
    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


class AssemblyAIStreamingTranscriber:
    def __init__(self, websocket: WebSocket, loop, sample_rate=16000):
        self.websocket = websocket
        self.loop = loop

        self.client = StreamingClient(
            StreamingClientOptions(
                api_key=aai.settings.api_key,
                api_host="streaming.assemblyai.com"
            )
        )
        self.client.on(StreamingEvents.Begin, self.on_begin)
        self.client.on(StreamingEvents.Turn, self.on_turn)
        self.client.on(StreamingEvents.Termination, self.on_termination)
        self.client.on(StreamingEvents.Error, self.on_error)

        self.client.connect(
            StreamingParameters(sample_rate=sample_rate, format_turns=True)
        )

    def on_begin(self, client, event: BeginEvent):
        print(f"🎤 Session started: {event.id}")

    def on_turn(self, client, event: TurnEvent):
        if event.end_of_turn and event.transcript.strip():
            user_text = event.transcript

            # Print user speech in VS Code terminal
            print("\nUser:", user_text)

            # Send transcript to frontend
            asyncio.run_coroutine_threadsafe(
                self.websocket.send_json({"type": "transcript", "text": user_text}),
                self.loop
            )

            # Stream LLM response
            def run_llm_stream():
                try:
                    for chunk in gemini_model.generate_content(user_text, stream=True):
                        if chunk.text:
                            # Print LLM response in VS Code terminal
                            print("LLM:", chunk.text, end="", flush=True)
                            # Send LLM response to frontend
                            asyncio.run_coroutine_threadsafe(
                                self.websocket.send_json({"type": "ai_response", "text": chunk.text}),
                                self.loop
                            )
                except Exception as e:
                    print("⚠️ Gemini streaming error:", e)

            threading.Thread(target=run_llm_stream, daemon=True).start()

    def on_termination(self, client, event: TerminationEvent):
        print(f"\n🛑 Session terminated after {event.audio_duration_seconds} s")

    def on_error(self, client, error: StreamingError):
        print("❌ Error:", error)

    def stream_audio(self, audio_chunk: bytes):
        self.client.stream(audio_chunk)

    def close(self):
        self.client.disconnect(terminate=True)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_event_loop()
    transcriber = AssemblyAIStreamingTranscriber(websocket, loop)

    try:
        while True:
            data = await websocket.receive_bytes()
            transcriber.stream_audio(data)
    except WebSocketDisconnect:
        print("Client disconnected")
        transcriber.close()
