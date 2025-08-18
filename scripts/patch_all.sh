#!/usr/bin/env bash
set -euo pipefail
ROOT="$(pwd)"
TS="$(date +%Y%m%d-%H%M%S)"
echo "== SatpamBot ALL-IN-ONE v2 =="
# helpers
dst="$ROOT/satpambot/bot/modules/discord_bot/helpers/log_utils.py"
mkdir -p "$(dirname "$dst")"; cp "satpambot/bot/modules/discord_bot/helpers/log_utils.py" "$dst"
echo "[1/5] helpers/log_utils.py updated"
# cogs
for f in presence_sticky.py status_sticky_auto.py presence_clock_sticky.py presence_fix.py; do
  src="satpambot/bot/modules/discord_bot/cogs/$f"; dst="$ROOT/satpambot/bot/modules/discord_bot/cogs/$f"
  mkdir -p "$(dirname "$dst")"; cp "$src" "$dst"
done
echo "[2/5] presence cogs unified (all call helper)"
# 404 templates
for tpl in "satpambot/dashboard/templates/404.html" "templates/404.html"; do
  dst="$ROOT/$tpl"; mkdir -p "$(dirname "$dst")"; cp "$tpl" "$dst"
done
echo "[3/5] 404 templates ensured"
# root app patch
APP="$ROOT/app.py"
if [[ -f "$APP" ]]; then
  cp "$APP" "$APP.bak.$TS"
  if ! grep -q "## PATCH: root-app v2" "$APP"; then
cat >> "$APP" <<'PYAPP'
# ## PATCH: root-app v2 (healthz + template/static mapping + safe 404)
try:
    import os as _os
    from jinja2 import ChoiceLoader as _ChoiceLoader, FileSystemLoader as _FileSystemLoader, TemplateNotFound as _TemplateNotFound
    _BASE_DIR = _os.path.dirname(__file__)
    _TPL_DIR = _os.path.join(_BASE_DIR, "satpambot", "dashboard", "templates")
    _STA_DIR = _os.path.join(_BASE_DIR, "satpambot", "dashboard", "static")
    if _os.path.isdir(_TPL_DIR):
        try: app.jinja_loader = _ChoiceLoader([app.jinja_loader, _FileSystemLoader(_TPL_DIR)])
        except Exception: app.jinja_env.loader = _ChoiceLoader([app.jinja_env.loader, _FileSystemLoader(_TPL_DIR)])
    if _os.path.isdir(_STA_DIR):
        try:
            from flask import send_from_directory as _sfd
            app.add_url_rule("/static/<path:filename>", "static_custom", lambda filename: _sfd(_STA_DIR, filename))
        except Exception: pass
    if "healthz" not in app.view_functions:
        @app.get("/healthz")
        def healthz(): return "ok", 200
    if "metrics" not in app.view_functions:
        import psutil as _psutil
        @app.get("/metrics")
        def metrics():
            cpu = _psutil.cpu_percent(interval=0.05); mem = _psutil.virtual_memory()
            return {"cpu": cpu, "ram_mb": int(mem.used/1024/1024), "ram_total_mb": int(mem.total/1024/1024)}
    if "uptime" not in app.view_functions:
        from datetime import datetime as _dt; import time as _t
        _APP_START_TS = globals().get("_APP_START_TS", _t.time())
        @app.get("/uptime")
        def uptime():
            seconds = int(_t.time() - _APP_START_TS)
            return {"uptime_seconds": seconds, "started_at": _dt.utcnow().isoformat() + "Z"}
    @app.errorhandler(404)
    def _patched_not_found(e):
        try: return render_template("404.html"), 404
        except _TemplateNotFound: return "404 Not Found", 404
except Exception: pass
# ## END PATCH
PYAPP
    echo "[4/5] root app patched -> backup app.py.bak.$TS"
  else
    echo "[4/5] root app already patched (skip)"
  fi
else
  echo "[4/5] root app.py not found (skip)"
fi
# dashboard health (optional)
DASH="$ROOT/satpambot/dashboard/app_dashboard.py"
if [[ -f "$DASH" ]]; then
  if ! grep -q "def healthz" "$DASH"; then
cat >> "$DASH" <<'PYAPP'
# --- patched endpoints: health & metrics ---
from datetime import datetime; import psutil
@app.get("/healthz")
def healthz(): return "ok", 200
@app.get("/metrics")
def metrics():
    cpu = psutil.cpu_percent(interval=0.05); mem = psutil.virtual_memory()
    return {"cpu": cpu, "ram_mb": int(mem.used/1024/1024), "ram_total_mb": int(mem.total/1024/1024)}
@app.get("/uptime")
def uptime():
    global _APP_START_TS
    try: _APP_START_TS
    except NameError:
        import time as _t; _APP_START_TS = _t.time()
    import time as _t; seconds = int(_t.time() - _APP_START_TS)
    from datetime import datetime; return {"uptime_seconds": seconds, "started_at": datetime.utcnow().isoformat() + "Z"}
try:
    from jinja2 import TemplateNotFound
    @app.errorhandler(404)
    def _not_found(e):
        try: return render_template("404.html"), 404
        except TemplateNotFound: return "404 Not Found", 404
except Exception: pass
PYAPP
    echo "[5/5] dashboard app patched"
  else
    echo "[5/5] dashboard app already has health endpoints (skip)"
  fi
else
  echo "[5/5] dashboard app not found (skip)"
fi
echo "== DONE =="
