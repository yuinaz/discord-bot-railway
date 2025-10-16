
# Persona + Skills + Providers (API-only) — Render Free Pack

## Folders
- `satpambot/config/personas/*.yaml` — Persona konfigurasi (hot-reload via polling).
- `satpambot/bot/persona/loader.py` — Loader persona.
- `satpambot/bot/skills/registry.py` + `a06_skills_registry_overlay.py` — Registri skill ringan.
- `satpambot/bot/providers/{llm,stt,tts}.py` + `a06_providers_facade_overlay.py` — Facade ke GROQ/Gemini + ElevenLabs.

## ENV (opsional, aman di Render Free)
- Persona:
  - `PERSONA_DIR=satpambot/config/personas`
  - `PERSONA_ACTIVE_NAME=default`
  - `PERSONA_POLL_SEC=5`
- LLM:
  - `LLM_PROVIDER=groq|gemini`
  - `GROQ_API_KEY=...`, `GROQ_MODEL=llama-3.1-8b-instant`
  - `GOOGLE_API_KEY=...`, `GEMINI_MODEL=gemini-1.5-flash`
- STT (Groq Whisper):
  - `STT_MODEL=whisper-large-v3`
- TTS (ElevenLabs, opsional):
  - `ELEVENLABS_API_KEY=...`
  - `TTS_VOICE_ID=21m00Tcm4TlvDq8ikWAM`

## Integrasi (tanpa modif besar pada cogs lain)
- **Persona**: 
  ```python
  persona = bot.get_cog("PersonaOverlay").get_active_persona() if bot.get_cog("PersonaOverlay") else {}
  prefix = (persona.get("prompt_prefix") or "")
  suffix = (persona.get("prompt_suffix") or "")
  ```
- **LLM**:
  ```python
  prov = bot.get_cog("ProvidersOverlay")
  text = await prov.llm.generate(system_prompt=prefix, messages=[{"role":"user","content":question}])
  ```
- **Skills**:
  ```python
  from satpambot.bot.skills.registry import call
  await call("xp_award", bot, user_id, amount=5, reason="qna")
  ```
- **STT/TTS** (opsional, kirim file audio):
  ```python
  audio_bytes = await prov.tts.synth("Halo!")
  # kirim sebagai attachment ke Discord
  ```
