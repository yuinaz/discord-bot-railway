# SatpamBot Dashboard on Render.com

This bundle lets you deploy the **dashboard-only** Flask app to Render.

## Deploy (Render Blueprint)

1. Push your repository to GitHub (or any Git provider Render supports).
2. Add these files at the repo root:
   - `render.yaml`
   - `app.py`
   - `requirements.txt`
3. Ensure your project tree includes the package `satpambot/dashboard/...` (from your repo). This bundle also includes a patched `satpambot/dashboard/webui.py` as a fallback.
4. Go to **Render → New → Blueprint** and point it to your repo. Render will detect `render.yaml`.

### What this does
- Creates a Web Service named **satpambot-dashboard**
- Installs deps from `requirements.txt`
- Starts via `gunicorn app:app` and binds to `$PORT` as required by Render
- Stores data in `/opt/render/project/data` (set via `DATA_DIR` env var)

### Health & URLs
- Health: `HEAD /healthz` → 200
- Uptime: `GET /uptime` → ok
- Dashboard: `GET /dashboard`

## Live Metrics Ingest
Render sets a random `$METRICS_INGEST_TOKEN` on first deploy (see **Environment** tab). Post metrics from anywhere:

```bash
curl -X POST "$RENDER_URL/dashboard/api/metrics-ingest"   -H "Content-Type: application/json"   -H "X-Token: $METRICS_INGEST_TOKEN"   -d '{"guilds":12,"members":4310,"online":523,"channels":184,"threads":9,"latency_ms":87}'
```

> Replace `$RENDER_URL` with your Render service URL, e.g. `https://satpambot-dashboard.onrender.com`

## pHash Upload
- File: `POST /dashboard/api/phash/upload` (form-data key: `file`)
- URL: `POST /dashboard/api/phash/upload` body: `{ "url": "https://..." }`

## Banned Users
- API: `GET /dashboard/api/banned_users?limit=50`

## Local run (optional)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py  # http://127.0.0.1:5000
```
