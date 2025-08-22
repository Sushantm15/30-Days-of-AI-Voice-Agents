import os, asyncio, websockets

MURF_API_KEY = "ap2_eade5a8a-7a23-47fc-bd9f-76eff7857f7e"
CONTEXT_ID = "test-context"
VOICE_ID = "en-US-natalie"
URL = f"wss://api.murf.ai/v1/speech/stream-input?api-key={MURF_API_KEY}&sample_rate=44100&channel_type=MONO&format=WAV&context_id={CONTEXT_ID}"

async def test():
    try:
        async with websockets.connect(URL) as ws:
            print("✅ Connected successfully!")
            await ws.send('{"voice_config": {"voiceId": "' + VOICE_ID + '"}}')
            print("🎤 Voice config sent")
    except Exception as e:
        print("❌ Connection failed:", e)

asyncio.run(test())
