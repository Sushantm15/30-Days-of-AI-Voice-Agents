import speech_recognition as sr
import tempfile

async def speech_to_text(file):
    recognizer = sr.Recognizer()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await file.read())
        tmp.flush()

        with sr.AudioFile(tmp.name) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
    return text
