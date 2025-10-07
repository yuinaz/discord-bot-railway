# SatpamBot — Flat Patch (Render Free compatible, migration-ready)

- **Build Command:** `bash scripts/build_render.sh` (unchanged)
- **Start Command:** `python main.py` (unchanged)
- **No nested patch folders.** Drop these files in repo root.

What this gives you
- Works on Render **and** off-Render (MiniPC, local) via `sitecustomize.py` that auto-loads `.env` and applies safe defaults.
- Ensures OpenAI Python SDK **1.x** is installed during build.
- Lightweight smoke checks (non-fatal).

Files
- `sitecustomize.py` — auto-runs on Python startup. Loads `.env` (if present) and sets safe defaults so the bot runs even without Render env.
- `.env.sample` — template for local/offline use. **Do not** commit secrets.
- `neuro_lite.toml` — conservative defaults (mention-only, no DM).
- `scripts/build_render.sh` — installs deps (`requirements.txt` + openai 1.x + python-dotenv) and runs smoke.
- `scripts/smoketest_render.py` — quick import checks.

Notes
- If environment variables exist (Render), they override `.env` and defaults.
- If `.env` exists (MiniPC/local), it is loaded automatically.
- If neither exists, safe defaults apply (stickers off, no DM).

Rollback: just remove these files.
