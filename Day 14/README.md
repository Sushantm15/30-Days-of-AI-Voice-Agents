# 🎤 AI Voice Assistant — 30 Days of AI Voice Agents (Day 14)

An end-to-end **AI Voice Assistant** built as part of the **#30DaysOfAIVoiceAgents** challenge.  
By Day 14, the project has been **refactored, cleaned up, and structured for maintainability**, making it easier to scale and collaborate.  

---

## 📌 Project Overview

The AI Voice Assistant:
- Listens to the user through a microphone.  
- Converts speech to text using **Speech-to-Text (STT)** APIs.  
- Sends the transcription to an **LLM** for generating intelligent responses.  
- Converts the LLM’s response into speech using **Text-to-Speech (TTS)**.  
- Plays the audio back to the user in real-time.  
- Features a **modern UI** (introduced on Day 12).  
- Now has **refactored backend code** (Day 14) for better structure and maintainability.  

---

## 🛠️ Technologies Used

**Frontend**
- HTML5, CSS3, JavaScript  
- MediaRecorder API for audio capture  
- Fetch API for server communication  

**Backend**
- Python 3.10+  
- FastAPI for API endpoints  
- `uvicorn` as the ASGI server  

**APIs**
- **Speech-to-Text (STT):** AssemblyAI  
- **Large Language Model (LLM):** Google Gemini  
- **Text-to-Speech (TTS):** Murf AI  

**Other**
- **Error Handling** – robust exception handling in backend  
- **Logging** – better debugging and tracking  
- **.env file** – stores API keys securely  
- **Requirements.txt** – project dependencies  

---

## 🏗️ Architecture

![Architecture Diagram](images/Architecture.png)

---

## ✨ Key Features (Day 14 Updates)

- **🧹 Refactored Codebase** – Organized into `services/` folder for STT, LLM, and TTS logic.  
- **📦 Pydantic Models** – Request/Response schemas for API endpoints.  
- **🛡️ Error Handling** – Clean `try/except` blocks for graceful failure handling.  
- **📝 Logging** – Better logs for debugging and monitoring.  
- **🚀 GitHub Integration** – Code cleaned up and pushed to a public repository.  

---

##How to Run

1️⃣ Clone the repository

git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>


2️⃣ Create virtual environment

python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows


3️⃣ Install dependencies

pip install -r requirements.txt


4️⃣ Set environment variables
Create a .env file in the project root:

ASSEMBLYAI_API_KEY=your_assemblyai_key
GEMINI_API_KEY=your_gemini_key
MURFAI_API_KEY=your_murfai_key


5️⃣ Run the backend

uvicorn main:app --reload


6️⃣ Open the frontend

Open index.html in your browser

Allow microphone access

Click 🎤 Start Recording and talk to your assistant

##📦 Folder Structure (Refactored)

│── Day 14/
│   │── index.html           # Frontend UI
│   │── main.py              # FastAPI backend entry point
│   │── requirements.txt     # Dependencies
│   │── .env                 # API keys
│   │── services/            # Refactored services
│   │   │── stt_service.py   # Handles Speech-to-Text
│   │   │── llm_service.py   # Handles Google Gemini
│   │   │── tts_service.py   # Handles Murf AI
│   │
│   │── models/              # Pydantic schemas
│   │   │── request.py
│   │   │── response.py
│
│── images/                  # Project screenshots & architecture diagrams
│   │── Architecture.png
│
│── README.md                # Project documentation


📬 Connect

If you’re building AI voice agents or working on conversational AI, I’d love to connect!

📧 Email: sushantmore1503@example.com
🔗 LinkedIn: www.linkedin.com/in/sushantmore15

#AI #VoiceTech #ConversationalAI #FastAPI #AssemblyAI #GoogleGemini #MurfAI #SpeechToText #TextToSpeech #MachineLearning #Python #VoiceAgents #ErrorHandling #OpenSource #30DaysOfAIVoiceAgents
