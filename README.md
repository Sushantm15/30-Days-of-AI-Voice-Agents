# 🎤 SoulDAm's AI Chatbot — Complete Project

An end-to-end **AI Voice Assistant** built as part of the **#30DaysOfAIVoiceAgents** challenge.  
This project combines **speech recognition, large language models, and text-to-speech** to create a fully interactive conversational agent.

---

## 📌 Project Overview

The SouLDMan's AI Chatbot:
- Listens to the user through a microphone.
- Converts speech to text using **Speech-to-Text (STT)** APIs.
- Sends the transcription to an **LLM** for generating intelligent responses.
- Converts the LLM’s response into speech using **Text-to-Speech (TTS)**.
- Plays the audio back to the user in real-time.
- Features a **revamped UI** for a modern, clean, and interactive experience.

---

## 🛠️ Technologies Used

**Frontend**
- HTML5, CSS3, JavaScript
- MediaRecorder API for audio capture
- Fetch API for server communication

**Backend**
- Python 3.10+
- Flask for API endpoints
- `gTTS` for text-to-speech
- `requests` for API calls

**APIs**
- **Speech-to-Text (STT):** AssemblyAI
- **Large Language Model (LLM):** OpenAI / Google Gemini
- **Text-to-Speech (TTS):** Murf AI
- **Weather Data:** OpenWeather API

**Other**
- Fallback audio mechanism for error handling
- Environment variable configuration for API keys
- Dynamic persona system for varied responses

---

## 🏗️ Architecture

![Architecture Diagram](images/Architecture.png)

---

## ✨ Key Features

- **🎤 Voice Recording & Processing** – Record user audio directly from the browser and send it to the backend for processing.
- **🗣️ Speech-to-Text (STT)** – Convert spoken input to text using AssemblyAI API.
- **💬 Conversational AI** – Process user queries with OpenAI LLM for intelligent responses.
- **🔊 Text-to-Speech (TTS)** – Generate natural-sounding audio replies with Murf AI.
- **⚡ Real-time Interaction** – Fast request/response cycle for a smooth conversational experience.
- **🛡️ Robust Error Handling** – Gracefully handle STT, LLM, and TTS failures with fallback audio messages.
- **🎨 Modern UI Design** – Clean, responsive, and interactive frontend with persona selection and voice interaction.
- **🔄 Single Record/Stop Button** – Simplified recording control with dynamic state changes.
- **🎬 Auto Audio Playback** – Automatically plays AI-generated responses without manual play clicks.
- **🌍 Weather & Time Skills** – Fetches real-time weather and local time dynamically.
- **🧑‍💻 Dynamic API Key Configuration** – Users can set OpenAI, Murf AI, AssemblyAI, and OpenWeather API keys directly from the UI.
- **📂 Modular Folder Structure** – Each day’s folder contains its own `index.html`, backend script, and dependencies for easy tracking.

---

## 🖼️ Screenshots

![UI Screenshot](images/ui_screenshot.png)

---

## 📌 Blog & Project Showcase

Check out the blog about this project on LinkedIn:  
[AI Voice Assistant Blog](https://www.linkedin.com/feed/update/urn:li:activity:7367748798464421888?updateEntityUrn=urn%3Ali%3Afs_updateV2%3A%28urn%3Ali%3Aactivity%3A7367748798464421888%2CFEED_DETAIL%2CEMPTY%2CDEFAULT%2Cfalse%29)

---

## How to Run

1️⃣ Clone the repository  

git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
2️⃣ Install dependencies

pip install -r requirements.txt

3️⃣ Set environment variables

Create a .env file in the project root:

OPENAI_API_KEY=your_openai_key
ASSEMBLYAI_API_KEY=your_assemblyai_key
MURFAI_API_KEY=your_murfai_key
OPENWEATHER_API_KEY=your_openweather_key

4️⃣ Run the backend

python main.py

5️⃣ Open the frontend

Open index.html in your browser

Allow microphone access

Click the 🎤 Speak button and interact with your assistant

📦 Folder Structure
yaml
Copy code
│── Day 1/
│   │── index.html       # Frontend UI
│   │── main.py          # Backend script
│   │── requirements.txt
│
│── Day 2/
│   │── index.html
│   │── main.py
│   │── requirements.txt
│
│── ...
│
│── images/              # Project screenshots & architecture diagrams
│   │── Architecture.png
│   │── Screenshot 2025-08-29 083241.png
│
│── README.md            # Project documentation
📬 Connect

If you’re building AI voice agents or working on conversational AI, I’d love to connect!
📧 Email: sushantmore1503@example.com
🔗 LinkedIn: www.linkedin.com/in/sushantmore15

#AI #VoiceTech #ConversationalAI #Flask #OpenAI #AssemblyAI #MurfAI #gTTS #SpeechToText #TextToSpeech #MachineLearning #Python #VoiceAgents #30DaysOfAIVoiceAgents
