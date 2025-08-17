import os
from gtts import gTTS

OUTPUT_FILE = "app/static/output.mp3"

def text_to_speech(text: str) -> str:
    """Convert text to speech and save as an MP3 file."""
    if not text.strip():
        raise ValueError("Text for TTS is empty")

    tts = gTTS(text=text, lang="en")
    tts.save(OUTPUT_FILE)

    return OUTPUT_FILE
