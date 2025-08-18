#!/usr/bin/env bash
set -euo pipefail
ROOT="$(pwd)"
APP="$ROOT/satpambot/dashboard/app_dashboard.py"
BACKUP="$APP.bak.$(date +%Y%m%d-%H%M%S)"

echo "== Patch SatpamBot4 =="

if [[ -f "$APP" ]]; then
  cp "$APP" "$BACKUP"
  echo "[1/4] Backup -> $BACKUP"
else
  echo "[1/4] ERROR: $APP tidak ditemukan" >&2
  exit 1
fi

if ! grep -q "def healthz" "$APP"; then
cat >> "$APP" <<'PYAPP'

# --- patched endpoints: health & metrics ---
from datetime import datetime
import psutil

@app.get("/healthz")
def healthz():
    return "ok", 200

@app.get("/metrics")
def metrics():
    cpu = psutil.cpu_percent(interval=0.05)
    mem = psutil.virtual_memory()
    return {"cpu": cpu, "ram_mb": int(mem.used/1024/1024), "ram_total_mb": int(mem.total/1024/1024)}

@app.get("/uptime")
def uptime():
    global _APP_START_TS
    try:
        _APP_START_TS
    except NameError:
        import time as _t; _APP_START_TS = _t.time()
    seconds = int(__import__("time").time() - _APP_START_TS)
    return {"uptime_seconds": seconds, "started_at": datetime.utcnow().isoformat() + "Z"}

# 404 fallback (keep it last)
try:
    from jinja2 import TemplateNotFound  # type: ignore
    @app.errorhandler(404)
    def _not_found(e):
        try:
            return render_template("404.html"), 404
        except TemplateNotFound:
            return "404 Not Found", 404
except Exception:
    pass
PYAPP
  echo "[2/4] Tambah /healthz, /metrics, /uptime, dan 404 handler"
else
  echo "[2/4] Endpoints sudah ada, skip"
fi

TPL_DIR="$ROOT/satpambot/dashboard/templates"
mkdir -p "$TPL_DIR"
if [[ ! -f "$TPL_DIR/404.html" ]]; then
  cp "satpambot/dashboard/templates/404.html" "$TPL_DIR/404.html"
  echo "[3/4] Tambah templates/404.html"
else
  echo "[3/4] 404.html sudah ada, skip"
fi

LOG_UTILS_DST="$ROOT/satpambot/bot/modules/discord_bot/helpers/log_utils.py"
mkdir -p "$(dirname "$LOG_UTILS_DST")"
cp "satpambot/bot/modules/discord_bot/helpers/log_utils.py" "$LOG_UTILS_DST"
echo "[4/4] Replace helpers/log_utils.py (unify sticky presence)"

echo "Done."
