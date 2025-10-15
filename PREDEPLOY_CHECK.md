# Predeploy check & quick fixes (2025-10-07)

**What I changed in this patch:**
1. `satpambot/bot/modules/discord_bot/ai/chatgpt_handler.py` — migrated to the new OpenAI SDK via your adapter (`openai_v1_adapter.chat_completion_create`). This removes the legacy `openai.ChatCompletion` calls which will break on `openai>=1.0` (your Render pin is `openai==2.2.0`).  
2. `scripts/smoke_cogs.py` — replaced with a minimal, asyncio‑safe, dependency‑free importer so you can smoke‑test cogs even without discord.py installed (works in notebooks/CI too).

**Sanity checks to run locally before push:**

```bash
# 1) Ensure deps (local)
python -m pip install -r requirements.latest.local310.txt

# 2) Translator import smoke
python scripts/smoke_translator.py

# 3) Cogs smoke (all) — or cherry-pick critical ones
python scripts/smoke_cogs.py
python scripts/smoke_cogs.py --only translator,anti_image_phash_runtime,first_touch_attachment_ban,anti_image_scored_guard,temp_dismiss_log,repo_guild_sync_bootstrap
```

**Notes:**
- Threads are already exempted in many modules; your tree shows 20+ cogs with `discord.Thread` early‑return guards.
- Render Procfile is `web: gunicorn app:app` which is fine for dashboard‑only; the bot process should run on your mini‑PC as planned.
- If you previously saw the `openai.ChatCompletion` deprecation warnings from `chat_neurolite`, leave it enabled — it already uses an adapter in your tree. The patched `chatgpt_handler.py` now does too.
