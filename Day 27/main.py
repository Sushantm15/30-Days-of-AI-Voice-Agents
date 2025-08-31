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

@app.route("/")
def index():
    return html_content

html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SoulDMan's AI Chatbot</title>
<style>
    body {
        font-family: 'Segoe UI', Tahoma, sans-serif;
        background: #0f172a;
        color: #fff;
        margin: 0;
        padding: 0;
    }
    .chat-container {
        max-width: 800px;
        margin: 30px auto;
        background: #1e293b;
        border-radius: 16px;
        display: flex;
        flex-direction: column;
        height: 85vh;
        overflow: hidden;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
    }
    .header {
        background: linear-gradient(90deg, #2563eb, #9333ea);
        padding: 15px;
        font-size: 20px;
        font-weight: bold;
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: #fff;
    }
    .header button {
        background: rgba(255,255,255,0.2);
        border: none;
        border-radius: 8px;
        padding: 8px 14px;
        color: #fff;
        font-weight: bold;
        cursor: pointer;
        transition: background 0.2s ease;
    }
    .header button:hover {
        background: rgba(255,255,255,0.4);
    }
    .chat-box {
        flex: 1;
        padding: 20px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 12px;
    }
    .message {
        max-width: 75%;
        padding: 12px 16px;
        border-radius: 14px;
        font-size: 15px;
        line-height: 1.4;
    }
    .bot {
        background: #334155;
        align-self: flex-start;
        border-top-left-radius: 0;
    }
    .user {
        background: #2563eb;
        align-self: flex-end;
        border-top-right-radius: 0;
    }
    .controls {
        padding: 12px;
        background: #1e293b;
        display: flex;
        justify-content: center;
        gap: 10px;
        border-top: 1px solid #334155;
        flex-wrap: wrap;
    }
    select, button {
        padding: 10px 14px;
        border-radius: 10px;
        border: none;
        font-size: 14px;
        cursor: pointer;
    }
    select {
        background: #334155;
        color: #fff;
    }
    button {
        background: #2563eb;
        color: #fff;
        font-weight: bold;
        transition: background 0.2s ease;
    }
    button:hover {
        background: #1d4ed8;
    }
    audio {
        margin-top: 8px;
        display: block;
    }
    /* Config Modal */
    .modal {
        display: none;
        position: fixed;
        z-index: 200;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.7);
        justify-content: center;
        align-items: center;
    }
    .modal-content {
        background: #1e293b;
        padding: 24px;
        border-radius: 12px;
        width: 90%;
        max-width: 400px;
        text-align: center;
        box-shadow: 0 6px 20px rgba(0,0,0,0.4);
    }
    .modal-content h3 {
        margin-bottom: 16px;
        font-size: 20px;
    }
    .modal-content input {
        width: 90%;
        margin: 10px auto;
        display: block;
        padding: 10px;
        background: #334155;
        border: none;
        border-radius: 8px;
        color: #fff;
    }
    .modal-content button {
        margin: 10px;
        width: 40%;
    }
    @media (max-width: 600px) {
        .chat-container {
            height: 90vh;
            margin: 10px;
        }
        .controls {
            flex-direction: column;
        }
    }
</style>
</head>
<body>
<div class="chat-container">
    <div class="header">
        SoulDMan's AI Chatbot
        <button onclick="openConfig()">⚙ Config</button>
    </div>
    
    <div class="chat-box" id="chatBox"></div>

    <div class="controls" id="controlsSection">
        <select id="persona">
            <option value="pirate">Pirate 🏴‍☠️</option>
            <option value="cowboy">Cowboy 🤠</option>
            <option value="robot">Robot 🤖</option>
            <option value="wizard">Wizard 🧙‍♂️</option>
            <option value="detective">Detective 🕵️</option>
        </select>
        <button onclick="setPersona()">Set Persona</button>
        <button onclick="greet()">Greet</button>
        <button onclick="startSpeech()">🎤 Speak</button>
    </div>
</div>

<!-- Config Modal -->
<div class="modal" id="configModal">
    <div class="modal-content">
        <h3>🔑 API Configuration</h3>
        <input type="password" id="openaiKey" placeholder="OpenAI API Key">
        <input type="password" id="openweatherKey" placeholder="OpenWeather API Key">
        <div>
            <button onclick="saveKeys()">Save</button>
            <button onclick="closeConfig()">Close</button>
        </div>
    </div>
</div>

<script>
    const API_URL = "http://127.0.0.1:5000/api";
    let currentPersona = "pirate";

    let apiKeys = {
        openai: localStorage.getItem("openaiKey") || "",
        openweather: localStorage.getItem("openweatherKey") || ""
    };

    function loadKeysIntoModal() {
        document.getElementById('openaiKey').value = apiKeys.openai;
        document.getElementById('openweatherKey').value = apiKeys.openweather;
    }

    function addMessage(text, audioUrl = null, sender = 'bot') {
        const chatBox = document.getElementById('chatBox');
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}`;
        msgDiv.innerHTML = text;
        chatBox.appendChild(msgDiv);
        if (audioUrl) {
            const audio = document.createElement('audio');
            audio.src = audioUrl;
            audio.autoplay = true;
            chatBox.appendChild(audio);
        }
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    async function setPersona() {
        currentPersona = document.getElementById('persona').value;
        const res = await fetch(`${API_URL}/set_persona`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "x-openai-key": apiKeys.openai,
                "x-openweather-key": apiKeys.openweather
            },
            body: JSON.stringify({persona: currentPersona})
        });
        const data = await res.json();
        addMessage(data.message || data.error);
    }

    async function greet() {
        const res = await fetch(`${API_URL}/greet`, {
            headers: {
                "x-openai-key": apiKeys.openai,
                "x-openweather-key": apiKeys.openweather
            }
        });
        const data = await res.json();
        addMessage(data.text, `http://127.0.0.1:5000${data.audio_url}`);
    }

    function startSpeech() {
        if (!('webkitSpeechRecognition' in window)) {
            alert("Speech Recognition not supported.");
            return;
        }
        const recognition = new webkitSpeechRecognition();
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onresult = async function(event) {
            const speechResult = event.results[0][0].transcript;
            addMessage(`You: ${speechResult}`, null, 'user');
            const res = await fetch(`${API_URL}/respond`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "x-openai-key": apiKeys.openai,
                    "x-openweather-key": apiKeys.openweather
                },
                body: JSON.stringify({message: speechResult})
            });
            const data = await res.json();
            addMessage(data.text, `http://127.0.0.1:5000${data.audio_url}`);
        };

        recognition.onerror = function(event){
            console.error(event.error);
            alert("Speech recognition error: " + event.error);
        };

        recognition.start();
    }

    function openConfig() {
        loadKeysIntoModal();
        document.getElementById('configModal').style.display = 'flex';
    }

    function closeConfig() {
        document.getElementById('configModal').style.display = 'none';
    }

    function showSkillButtons() {
        if(document.getElementById("skillButtonsContainer")) return;
        const controls = document.getElementById('controlsSection');
        const container = document.createElement("div");
        container.id = "skillButtonsContainer";
        container.style.display = "flex";
        container.style.gap = "10px";
        container.style.marginTop = "10px";

        const weatherBtn = document.createElement("button");
        weatherBtn.innerText = "🌤 Weather (India)";
        weatherBtn.onclick = fetchWeatherIndia;

        const timeBtn = document.createElement("button");
        timeBtn.innerText = "⏰ Time (India)";
        timeBtn.onclick = showTimeIndia;

        container.appendChild(weatherBtn);
        container.appendChild(timeBtn);
        controls.appendChild(container);
    }

    async function fetchWeatherIndia() {
        if (!apiKeys.openweather) { alert("OpenWeather API key not set!"); return; }
        try {
            const res = await fetch(`${API_URL}/weather_india`, {
                headers: {"x-openweather-key": apiKeys.openweather}
            });
            const data = await res.json();
            if(data.weather && data.temp) {
                addMessage(`Weather in India: ${data.weather}, Temp: ${data.temp}°C`);
            } else {
                addMessage("Error fetching weather for India.");
            }
        } catch (err) {
            console.error(err);
            addMessage("Error fetching weather for India.");
        }
    }

    function showTimeIndia() {
        const indiaTime = new Date().toLocaleString("en-US", {timeZone: "Asia/Kolkata"});
        addMessage(`Current time in India: ${indiaTime}`);
    }

    async function saveKeys() {
        const openaiKey = document.getElementById('openaiKey').value.trim();
        const openweatherKey = document.getElementById('openweatherKey').value.trim();
        if (openaiKey) { apiKeys.openai = openaiKey; localStorage.setItem("openaiKey", openaiKey);}
        if (openweatherKey) { apiKeys.openweather = openweatherKey; localStorage.setItem("openweatherKey", openweatherKey);}
        
        const res = await fetch(`${API_URL}/update_keys`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({openai_key: apiKeys.openai, openweather_key: apiKeys.openweather})
        });
        const data = await res.json();
        alert(data.message || "Keys updated!");
        closeConfig();
        showSkillButtons();
    }

    if(apiKeys.openai || apiKeys.openweather) { showSkillButtons(); }
</script>
</body>
</html>

"""

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


# ----------- New endpoint for India weather ----------
@app.route("/api/weather_india", methods=["GET"])
def weather_india():
    if not agent.openweather_api_key:
        return jsonify({"error": "OpenWeather API key not configured"}), 400
    try:
        city = "Delhi"  # default city in India
        data = requests.get(
            f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={agent.openweather_api_key}&units=metric"
        ).json()
        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        return jsonify({"weather": desc, "temp": temp})
    except Exception as e:
        return jsonify({"error": f"Failed to fetch weather: {str(e)}"}), 500
# ------------------------------------------------------


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
