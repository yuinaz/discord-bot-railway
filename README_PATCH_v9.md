
# Patch: Phish DnD (file/link) + Live Banlist + Metrics Ingest

What this patch does:
- Adds **/dashboard/api/phash/upload** (POST) to accept image file *or* JSON `{"url":"https://..."}`.
- Computes **pHash** (via `imagehash` if available, otherwise a safe fallback) and appends it to `data/phish_lab/phash_blocklist.json`.
- Stores uploaded images in `data/uploads/phish-lab/`.
- Adds **/dashboard/api/banned_users** (GET) to show latest ban events from either:
  - `data/bans.sqlite` (auto-discovers table/columns), or
  - `data/ban_events.jsonl` / `data/banlog.jsonl` / `data/ban_events.json`.
- Adds **/dashboard/api/metrics-ingest** (POST) for the bot to push JSON metrics, cached in `data/live_metrics.json`.
  - Optional header `X-Token` must equal env `METRICS_INGEST_TOKEN` if set.
- Improves front-end drag-and-drop to accept **files AND links**, plus **paste**.
- Injects a **Banned Users (live)** card into the Dashboard without needing to change templates.
- Keeps metrics counters updated every ~5s; banned list every ~10s.

## Files in this patch

- `satpambot/dashboard/static/js/dragdrop_phash.js` (replaced & enhanced)
- `satpambot/dashboard/webui.py.PATCH.txt` (code to merge into your existing `webui.py`)
- `scripts/smoketest_dashboard_routes.py`

## How to apply

1. Open `satpambot/dashboard/webui.py` in your project and paste the contents of
   `satpambot/dashboard/webui.py.PATCH.txt` into it **after** your blueprint is created.
   - If you already have `/api/metrics`, keep one version; they're compatible.
   - Ensure `dashboard_bp` name matches your blueprint variable.
2. Replace your JS at `satpambot/dashboard/static/js/dragdrop_phash.js` with the one from this patch.
3. (Optional) Add to `requirements.txt` if missing:
   ```
   pillow
   imagehash
   requests
   psutil
   ```
4. Run the smoketest:
   ```bash
   python scripts/smoketest_dashboard_routes.py
   ```
5. Restart your app.

## Bot-side (optional but recommended)

Point your `live_metrics_push.py` to POST JSON to `/dashboard/api/metrics-ingest`
(e.g., guilds, members, online, channels, threads, latency_ms). Example:

```python
import os, json, time, requests
URL = os.getenv("DASHBOARD_URL", "http://localhost:5000") + "/dashboard/api/metrics-ingest"
TOKEN = os.getenv("METRICS_INGEST_TOKEN", "")
def push(data):
    headers = {"X-Token": TOKEN} if TOKEN else {}
    try:
        requests.post(URL, json=data, headers=headers, timeout=5)
    except Exception:
        pass

# sample
push({"guilds": 1, "members": 123, "online": 7, "channels": 12, "threads": 3, "latency_ms": 42})
```

## Notes

- The "Make Things Simple!" card will be replaced client-side by the "Banned Users (live)" card.
- Drag & Drop now also supports dropping **a link** to an image (e.g., from your browser) and **pasting** an image.
- All new data is kept under `data/` so Render free plan storage is simple.
