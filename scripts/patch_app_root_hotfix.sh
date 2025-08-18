#!/usr/bin/env bash
set -euo pipefail
ROOT="$(pwd)"
APP="$ROOT/app.py"
TS="$(date +%Y%m%d-%H%M%S)"

if [[ ! -f "$APP" ]]; then
  echo "ERROR: app.py tidak ditemukan di root." >&2
  exit 1
fi

cp "$APP" "$APP.bak.$TS"
echo "[backup] -> app.py.bak.$TS"

# Sisipkan blok patch sekali saja
if ! grep -q "## PATCH: app-root hotfix" "$APP"; then
cat >> "$APP" <<'PYAPP'

# ## PATCH: app-root hotfix
# - perbaiki import discord bot (absolute package, fallback)
# - map template & static ke dashboard
# - tambahkan /healthz, /favicon.ico, /shutdown, dan 404 aman

try:
    import os as _os
    from flask import send_from_directory as _sfd, request as _req  # type: ignore
    from jinja2 import ChoiceLoader as _ChoiceLoader, FileSystemLoader as _FileSystemLoader, TemplateNotFound as _TemplateNotFound  # type: ignore

    # 1) template & static mapping
    _BASE_DIR = _os.path.dirname(__file__)
    _TPL_DIR = _os.path.join(_BASE_DIR, "satpambot", "dashboard", "templates")
    _STA_DIR = _os.path.join(_BASE_DIR, "satpambot", "dashboard", "static")
    if _os.path.isdir(_TPL_DIR):
        try:
            app.jinja_loader = _ChoiceLoader([app.jinja_loader, _FileSystemLoader(_TPL_DIR)])
        except Exception:
            app.jinja_env.loader = _ChoiceLoader([app.jinja_env.loader, _FileSystemLoader(_TPL_DIR)])
    if _os.path.isdir(_STA_DIR) and "static_custom" not in app.view_functions:
        app.add_url_rule("/static/<path:filename>", "static_custom", lambda filename: _sfd(_STA_DIR, filename))

    # 2) favicon route (hindari 404)
    if "favicon" not in app.view_functions:
        @app.get("/favicon.ico")
        def favicon():
            fn = _os.path.join(_STA_DIR, "favicon.ico")
            if _os.path.isfile(fn):
                return _sfd(_STA_DIR, "favicon.ico")
            return ("", 204)

    # 3) healthz (untuk uptime check)
    if "healthz" not in app.view_functions:
        @app.get("/healthz")
        def healthz():
            return "ok", 200

    # 4) safe 404 handler
    @app.errorhandler(404)
    def _patched_not_found(e):
        try:
            return render_template("404.html"), 404  # type: ignore[name-defined]
        except _TemplateNotFound:
            return "404 Not Found", 404

    # 5) /shutdown agar mudah stop di Windows dev server
    if "shutdown" not in app.view_functions:
        @app.post("/shutdown")
        def shutdown():
            func = _req.environ.get("werkzeug.server.shutdown")
            if func:
                func()
                return "shutting down...", 200
            return "server does not support shutdown", 501
except Exception as _e:
    pass

# Import helper bot (absolute package, fallback)
try:
    from satpambot.bot.modules.discord_bot import run_bot, bot_running  # type: ignore
except Exception:  # fallback legacy import path
    try:
        from modules.discord_bot import run_bot, bot_running  # type: ignore
    except Exception:
        def run_bot(*a, **kw): raise RuntimeError("Discord module not loaded (run_bot unavailable)")
        def bot_running(): return False

# ## END PATCH
PYAPP
  echo "[patch] blok hotfix ditambahkan"
else
  echo "[patch] sudah ada, skip"
fi

# Tambahkan fallback templates (jaga-jaga)
mkdir -p "$ROOT/templates" "$ROOT/satpambot/dashboard/templates"

if [[ ! -f "$ROOT/templates/404.html" ]]; then
  cat > "$ROOT/templates/404.html" <<'HTML'
<!doctype html><html><head><meta charset="utf-8"><title>404</title></head><body><h1>404</h1><p>Halaman tidak ditemukan.</p></body></html>
HTML
  echo "[templates] add root templates/404.html"
fi

if [[ ! -f "$ROOT/templates/login.html" ]]; then
  cat > "$ROOT/templates/login.html" <<'HTML'
<!doctype html><html><head><meta charset="utf-8"><title>Login</title></head>
<body><h1>Login</h1><form method="post" action="/login"><input name="username" placeholder="username"><input type="password" name="password" placeholder="password"><button type="submit">Login</button></form></body></html>
HTML
  echo "[templates] add root templates/login.html (fallback minimal)"
fi

echo "Done. Restart app kemudian tes: /login, /healthz, /favicon.ico"
