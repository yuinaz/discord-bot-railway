#!/usr/bin/env python3
import os
from satpambot.helpers.llm_clients import QnaClient
print("GEMINI_API_KEY set? ", bool(os.getenv("GEMINI_API_KEY")))
print("GROQ_API_KEY set?   ", bool(os.getenv("GROQ_API_KEY")))
print("GEMINI_MODEL: ", os.getenv("GEMINI_MODEL","gemini-1.5-flash"))
print("GROQ_MODEL:   ", os.getenv("GROQ_MODEL","llama-3.1-8b-instant"))
g = QnaClient()
print("Client priority:", "Gemini first" if g.gemini.available() else "Groq only" if g.groq.available() else "No providers available")
print("SMOKE_OK")
