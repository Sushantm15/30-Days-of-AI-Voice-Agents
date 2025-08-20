import google.generativeai as genai
import os

# Configure Gemini / LLM API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def query_llm(prompt: str) -> str:
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text
