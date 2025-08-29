#!/usr/bin/env python3
"""
AI Voice Agent with Personas, gTTS, and Weather Skill
"""

import os
from datetime import datetime
from gtts import gTTS
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# -------------------- CONFIG --------------------
OPENWEATHER_API_KEY = "YOUR_OPENWEATHERMAP_KEY"  # Replace with your key

# -------------------- AGENT --------------------
class EnhancedVoiceAgent:
    def __init__(self):
        self.personas = {
            "pirate": {"greeting": "Ahoy there, matey! Welcome aboard me ship!", "movie_quote": "\"But you have heard of me.\" — Pirates of the Caribbean"},
            "cowboy": {"greeting": "Howdy, partner! What brings ya to these parts?", "movie_quote": "\"I'm your huckleberry.\" — Tombstone"},
            "robot": {"greeting": "Greetings, human. I am ARIA-7, your artificial intelligence assistant.", "movie_quote": "\"Hi, I'm Chitti the Robot.\" — Enthiran"},
            "wizard": {"greeting": "Greetings, young apprentice! The ancient magic flows through me.", "movie_quote": "\"You're a wizard, Harry.\" — Harry Potter"},
            "detective": {"greeting": "Good day. I'm Inspector Holmes, and I notice everything.", "movie_quote": "\"The game is afoot.\" — Sherlock"}
        }
        self.current_persona = "pirate"
        self.audio_dir = "audio_outputs"
        os.makedirs(self.audio_dir, exist_ok=True)

    def set_persona(self, persona_name):
        if persona_name.lower() in self.personas:
            self.current_persona = persona_name.lower()
            return True
        return False

    def apply_persona_style(self, text):
        style = {
            "pirate": lambda t: f"Arrr! {t} Ye savvy?",
            "cowboy": lambda t: f"Well, I reckon {t.lower()}, partner.",
            "robot": lambda t: f"PROCESSING: {t} END TRANSMISSION.",
            "wizard": lambda t: f"By my ancient wisdom, {t} So the magic reveals!",
            "detective": lambda t: f"Elementary! {t} The evidence is clear."
        }
        return style.get(self.current_persona, lambda t: t)(text)

    def generate_speech(self, text):
        filename = f"{self.audio_dir}/voice_{self.current_persona}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        styled_text = self.apply_persona_style(text)
        try:
            tts = gTTS(text=styled_text, lang='en', slow=False)
            tts.save(filename)
            return filename
        except Exception as e:
            print("gTTS exception:", e)
            return None

    def greet(self):
        persona = self.personas[self.current_persona]
        text = f"{persona['greeting']} {persona['movie_quote']}"
        audio_file = self.generate_speech(text)
        return audio_file, text

    def get_weather(self, city="Mumbai"):
        # Hardcoded weather for Mumbai
        return f"The current weather in {city} is Rainy with a temperature of 27°C."

    def respond(self, user_input):
        # Check for weather queries
        if "weather" in user_input.lower():
            words = user_input.lower().split()
            city = "Mumbai"
            if "in" in words:
                idx = words.index("in") + 1
                if idx < len(words):
                    city = " ".join(words[idx:])
            message_text = self.get_weather(city)
        else:
            message_text = f"You said: {user_input}"

        audio_file = self.generate_speech(message_text)
        return audio_file, message_text

# -------------------- FLASK --------------------
app = Flask(__name__)
CORS(app)
agent = EnhancedVoiceAgent()

@app.route("/")
def index():
    return "AI Voice Agent with Personas and Weather Skill"

@app.route("/api/set_persona", methods=["POST"])
def set_persona():
    persona = request.json.get("persona", "")
    if agent.set_persona(persona):
        return jsonify({"message": f"Persona set to {persona}"})
    return jsonify({"error": "Invalid persona"}), 400

@app.route("/api/greet", methods=["GET"])
def greet():
    fn, text = agent.greet()
    audio_url = f"/audio/{os.path.basename(fn)}" if fn else None
    return jsonify({"text": text, "audio_url": audio_url})

@app.route("/api/respond", methods=["POST"])
def respond():
    msg = request.json.get("message", "")
    if not msg:
        return {"error": "No message"}, 400
    fn, text = agent.respond(msg)
    audio_url = f"/audio/{os.path.basename(fn)}" if fn else None
    return jsonify({"text": text, "audio_url": audio_url})

@app.route("/audio/<path:filename>")
def audio(filename):
    return send_from_directory(agent.audio_dir, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
