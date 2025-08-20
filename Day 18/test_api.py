import websockets
import asyncio
import os

API_KEY = os.getenv("ASSEMBLYAI_API_KEY")  # or paste directly

URL = f"wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

async def connect():
    async with websockets.connect(
        URL,
        extra_headers={"Authorization": API_KEY},   # 👈 must include this
    ) as ws:
        print("Connected to AssemblyAI Realtime API")

asyncio.run(connect())