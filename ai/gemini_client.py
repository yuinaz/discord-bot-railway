# satpambot/ai/gemini_client.py
import os
from google import genai

_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
)

def generate_text(prompt: str, model: str = "gemini-2.5-flash") -> str:
    resp = _client.models.generate_content(model=model, contents=prompt)
    return resp.text or ""

# optional: setting gaya output
def generate_system(prompt: str, sys: str = "Kamu asisten ramah. Jawab singkat."):
    resp = _client.models.generate_content(
        model="gemini-2.5-flash",
        config={"system_instruction": sys},
        contents=prompt,
    )
    return resp.text or ""
