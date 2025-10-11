# PATCH NOTES (zip 51 -> patched)
- Fix intents: `Intents.none()` -> `Intents.default()` + `message_content=True` (agar on_message & miner jalan).
- HotEnv v2: anti spam, dukung `SATPAMBOT_ENV_FILE=/dev/null` & `HOTENV_ENABLE=0`.
- Tambah `neuro_memory_core.py` (remember/recall/forget + auto-learn reply/reaction).
- Tambah `bot/llm/groq_client.py` (Groq async client + retry).
- Tambah `intents_probe.py` (opsional, cek event on_message masuk).