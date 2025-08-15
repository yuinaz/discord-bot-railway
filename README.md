
# SatpamBot — Monorepo (with original files kept)

Struktur:
```
/bot/           → Bot Discord (MODE=botmini)
/dashboard/     → Dashboard Flask
/original_src/  → Salinan utuh isi ZIP lama untuk tes lokal
.github/workflows/ → Deploy Hooks Render (path filter)
```

## Render
### Botmini (root: `bot/`)
Build: `pip install -r requirements.txt`  
Start: `MODE=botmini python main.py`  
Env: `DISCORD_TOKEN`, `SHARED_DASH_TOKEN`, `ERRORLOG_WEBHOOK_URL`, (opsional) `BOT_SUPERVISE=1`, `BOT_START_DELAY=10`, `QUIET_HEALTHZ=1`  
Auto Deploy: OFF (pakai Deploy Hook)

### Dashboard (root: `dashboard/`)
Build: `pip install -r requirements.txt`  
Start: `gunicorn "app:app" --bind 0.0.0.0:$PORT --workers 2 --threads 4`  
Env: `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `OAUTH_REDIRECT_URI`, `BOT_BASE_URL`, `SHARED_DASH_TOKEN`, `SESSION_SECRET`, (ops) `SUPER_ADMIN_USER`, `SUPER_ADMIN_PASS`  
Auto Deploy: OFF (pakai Deploy Hook)

## GitHub Secrets (untuk workflow)
- `RENDER_DASH_DEPLOY_HOOK` → Deploy Hook URL dashboard (Render → Settings)
- `RENDER_BOT_DEPLOY_HOOK`  → Deploy Hook URL bot

## Local testing
### Bot
```
cd bot
python -m venv .venv && . .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# set ENV (atau salin .env.example → .env)
python main.py
```

### Dashboard
```
cd dashboard
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
# set ENV (atau salin .env.example → .env)
python app.py  # atau: gunicorn "app:app" --bind 127.0.0.1:8000
```
