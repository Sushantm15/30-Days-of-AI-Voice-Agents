#!/usr/bin/env python3
"""
AI Voice Agent with Personas, gTTS, OpenAI Weather, Date-Time Skill,
and Dynamic API Key Config (Day 27 Revamp)
"""

import os
import urllib.parse
from datetime import datetime
from gtts import gTTS
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# -------------------- LOAD ENV --------------------
load_dotenv()

# Default keys from .env
DEFAULT_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

if not DEFAULT_OPENAI_API_KEY:
    print("⚠ Warning: Missing OPENAI_API_KEY in .env file.")
if not DEFAULT_OPENWEATHER_API_KEY:
    print("⚠ Warning: Missing OPENWEATHER_API_KEY in .env file.")


# -------------------- AGENT --------------------
class EnhancedVoiceAgent:
    def __init__(self):
        self.personas = {
            "pirate": {
                "greeting": "Ahoy there, matey! Welcome aboard me ship!",
                "movie_quote": "\"But you have heard of me.\" — Pirates of the Caribbean"
            },
            "cowboy": {
                "greeting": "Howdy, partner! What brings ya to these parts?",
                "movie_quote": "\"I'm your huckleberry.\" — Tombstone"
            },
            "robot": {
                "greeting": "Greetings, human. I am ARIA-7, your artificial intelligence assistant.",
                "movie_quote": "\"Hi, I'm Chitti the Robot.\" — Enthiran"
            },
            "wizard": {
                "greeting": "Greetings, young apprentice! The ancient magic flows through me.",
                "movie_quote": "\"You're a wizard, Harry.\" — Harry Potter"
            },
            "detective": {
                "greeting": "Ah, you've arrived. The clues were clear — I was expecting you.",
                "movie_quote": "\"The game is afoot.\" — Sherlock"
            }
        }
        self.current_persona = "pirate"
        self.audio_dir = "audio_outputs"
        os.makedirs(self.audio_dir, exist_ok=True)

        # API keys (dynamic)
        self.openai_api_key = DEFAULT_OPENAI_API_KEY
        self.openai_model = DEFAULT_OPENAI_MODEL
        self.openweather_api_key = DEFAULT_OPENWEATHER_API_KEY

    def configure_api_keys(self, openai_key=None, weather_key=None):
        if openai_key:
            self.openai_api_key = openai_key
        if weather_key:
            self.openweather_api_key = weather_key
        return True

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
        """Generate audio using gTTS"""
        filename = f"{self.audio_dir}/voice_{self.current_persona}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        styled_text = self.apply_persona_style(text)

        try:
            tts = gTTS(text=styled_text, lang='en', slow=False)
            tts.save(filename)
            return filename
        except Exception as e:
            print(f"gTTS exception: {e}")
            return None

    def greet(self):
        persona = self.personas[self.current_persona]
        text = f"{persona['greeting']} {persona['movie_quote']}"
        audio_file = self.generate_speech(text)
        return audio_file, text

    def get_weather(self, city):
        """Fetch real weather data from OpenWeather API"""
        if not self.openweather_api_key:
            return "Weather service API key is missing. Please configure it."

        try:
            city_encoded = urllib.parse.quote(city)
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city_encoded}&appid={self.openweather_api_key}&units=metric"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                temp = data["main"]["temp"]
                description = data["weather"][0]["description"]
                city_name = data["name"]
                return f"The current weather in {city_name} is {description} with a temperature of {temp}°C."
            else:
                return f"Unable to fetch weather for {city}. Please check the city name."
        except Exception as e:
            return f"Error fetching weather: {str(e)}"

    def get_datetime(self):
        now = datetime.now()
        return f"Current date is {now.strftime('%A, %d %B %Y')} and time is {now.strftime('%I:%M %p')}."

    def respond(self, user_input):
        user_lower = user_input.lower()
        if "weather" in user_lower:
            city = user_input.split("in")[-1].strip() if "in" in user_lower else "your city"
            message_text = self.get_weather(city)
        elif "time" in user_lower or "date" in user_lower:
            message_text = self.get_datetime()
        else:
            message_text = f"You said: {user_input}"
        audio_file = self.generate_speech(message_text)
        return audio_file, message_text


# -------------------- FLASK --------------------
app = Flask(__name__)
CORS(app)
agent = EnhancedVoiceAgent()


# Middleware: apply API keys from headers if sent
@app.before_request
def attach_dynamic_keys():
    openai_key = request.headers.get("x-openai-key")
    weather_key = request.headers.get("x-openweather-key")
    if openai_key or weather_key:
        agent.configure_api_keys(openai_key=openai_key, weather_key=weather_key)


@app.route("/")
def index():
    return "AI Voice Agent with gTTS, Personas, Dynamic API Config, OpenAI Weather, and Date-Time Skill"


# Unified config endpoint
@app.route("/api/update_keys", methods=["POST"])
def update_keys():
    data = request.json or {}
    openai_key = data.get("openai_key") or request.headers.get("x-openai-key")
    weather_key = data.get("openweather_key") or request.headers.get("x-openweather-key")
    agent.configure_api_keys(openai_key=openai_key, weather_key=weather_key)
    return jsonify({"message": "API keys updated successfully!"})


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


@app.route("/api/weather", methods=["POST"])
def weather():
    city = request.json.get("city", "")
    if not city:
        return jsonify({"error": "No city provided"}), 400
    message_text = agent.get_weather(city)
    audio_file = agent.generate_speech(message_text)
    audio_url = f"/audio/{os.path.basename(audio_file)}" if audio_file else None
    return jsonify({"text": message_text, "audio_url": audio_url})


@app.route("/api/datetime", methods=["GET"])
def datetime_api():
    message_text = agent.get_datetime()
    audio_file = agent.generate_speech(message_text)
    audio_url = f"/audio/{os.path.basename(audio_file)}" if audio_file else None
    return jsonify({"text": message_text, "audio_url": audio_url})


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
