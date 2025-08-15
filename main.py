import os, sys, threading, importlib, asyncio, inspect, logging
from werkzeug.serving import WSGIRequestHandler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, "satpambot"))

class NoPingWSGIRequestHandler(WSGIRequestHandler):
    def log_request(self, code='-', size='-'):
        if getattr(self, 'path', '').startswith('/ping'):
            return
        super().log_request(code, size)

logging.getLogger('werkzeug').setLevel(logging.WARNING)

def ensure_dirs():
    for rel in ("satpambot/dashboard/static/uploads", "satpambot/bot/data"):
        try: os.makedirs(os.path.join(BASE_DIR, rel), exist_ok=True)
        except Exception: pass

def try_start_bot():
    mode = os.getenv("MODE", "both").lower()
    if mode not in ("both", "bot", "botmini"):
        print(f"[INFO] MODE={mode} -> bot disabled"); return
    token = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")
    if not token:
        print("[INFO] BOT_TOKEN/DISCORD_TOKEN not set -> skip bot"); return
    def _run():
        try:
            candidates = [
                "satpambot.bot.main",
                "satpambot.bot.__main__",
                "modules.discord_bot.discord_bot",  # legacy
                "bot.main",
                "modules.discord_bot.__main__",
            ]
            for mod_name in candidates:
                try:
                    mod = importlib.import_module(mod_name)
                    for fn in ("main", "run_bot", "run", "start"):
                        if hasattr(mod, fn):
                            func = getattr(mod, fn)
                            if inspect.iscoroutinefunction(func): return asyncio.run(func())
                            res = func()
                            if inspect.iscoroutine(res): return asyncio.run(res)
                            return
                except Exception as e:
                    print(f"[WARN] bot entry {mod_name} failed: {e}")
            print("[INFO] No bot entrypoint matched; skip.")
        except Exception as e:
            print("[ERROR] Bot fatal:", e)
    supervise = os.getenv("BOT_SUPERVISE", "1") != "0"
    if supervise:
        async def supervise_loop():
            delay = int(os.getenv("BOT_RETRY_DELAY", "12"))
            while True:
                try:
                    await asyncio.to_thread(_run); return
                except Exception as e:
                    print("[ERROR] Bot crash:", e); await asyncio.sleep(delay)
        threading.Thread(target=lambda: asyncio.run(supervise_loop()), daemon=True).start()
    else:
        threading.Thread(target=_run, daemon=True).start()

def _bind_admin_login(app):
    """Simple admin login (username/password) tanpa OAuth."""
    import os
    from flask import request, session, redirect as _redirect, render_template_string
    user = os.getenv('ADMIN_USERNAME') or os.getenv('SUPER_ADMIN_USER')
    pwd  = os.getenv('ADMIN_PASSWORD') or os.getenv('SUPER_ADMIN_PASS')

    # Secret & cookies
    app.config.setdefault('SECRET_KEY', os.getenv('FLASK_SECRET_KEY', 'dev-key'))
    app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
    app.config.setdefault('SESSION_COOKIE_SECURE', True)

    @app.route('/admin/login', methods=['GET','POST'])
    def _admin_login():
        err = None
        if not user or not pwd:
            return render_template_string('<p>Set ADMIN_USERNAME/ADMIN_PASSWORD atau SUPER_ADMIN_USER/SUPER_ADMIN_PASS di Render.</p>')
        if request.method == 'POST':
            u = (request.form.get('username') or '').strip()
            p = (request.form.get('password') or '').strip()
            if u == user and p == pwd:
                session['is_admin'] = True
                session['admin_user'] = u
                return _redirect('/')
            err = 'Username / password salah'
        return render_template_string(
            '''<!doctype html><meta name=viewport content="width=device-width, initial-scale=1">
<style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Helvetica,Arial,sans-serif;background:#0b0e14;color:#e6e6e6;display:grid;place-items:center;height:100vh;margin:0}
.card{background:#141923;border:1px solid #222b3b;border-radius:16px;padding:24px;min-width:320px;box-shadow:0 8px 32px rgba(0,0,0,.35)}
input,button{width:100%;padding:10px 12px;border-radius:10px}
input{border:1px solid #334;background:#0f1320;color:#e6e6e6;margin-top:8px}
button{margin-top:12px;border:none;background:#5865F2;color:#fff;font-weight:600;cursor:pointer}
.err{color:#ff6b6b;margin:8px 0 0 0;font-size:.9rem}</style>
<div class=card><h2>Login Admin</h2>{% if err %}<div class=err>{{err}}</div>{% endif %}
<form method=POST><label>Username</label><input name=username autocomplete=username>
<label>Password</label><input name=password type=password autocomplete=current-password>
<button type=submit>Masuk</button></form></div>''',
            err=err)

    @app.route('/logout')
    def _admin_logout():
        session.clear(); return _redirect('/')

    @app.route('/login')
    def _login_alias():
        return _redirect('/admin/login', 302)

    @app.route('/discord/login')
    def _discord_login_alias():
        return _redirect('/admin/login', 302)
def serve_dashboard():
    import os, importlib
    from flask import Flask, redirect
    port = int(os.getenv("PORT", "10000"))

    # Coba import dashboard app
    candidates = ("satpambot.dashboard.app", "dashboard.app")
    mod = None
    for name in candidates:
        try:
            mod = importlib.import_module(name)
            break
        except Exception as _e:
            mod = None

    if mod is None:
        # Fallback mini-web
        mini = Flask("mini-web")
        try: _bind_admin_login(mini)
        except Exception: pass

        @mini.route("/")
        def _root():
            return redirect("/admin/login", 302)

        mini.run(host="0.0.0.0", port=port)
        return

    app = getattr(mod, "app", None)
    socketio = getattr(mod, "socketio", None)

    if app is None:
        mini = Flask("mini-web")
        try: _bind_admin_login(mini)
        except Exception: pass

        @mini.route("/")
        def _root():
            return redirect("/admin/login", 302)

        mini.run(host="0.0.0.0", port=port)
        return

    # Bind login fallback pada app dashboard
    try: _bind_admin_login(app)
    except Exception: pass

    if socketio is not None:
        try:
            socketio.run(app, host="0.0.0.0", port=port)
        except TypeError:
            socketio.run(app, host="0.0.0.0", port=port)
    else:
        app.run(host="0.0.0.0", port=port)

    port = int(os.getenv("PORT", "10000"))
    candidates = ("satpambot.dashboard.app", "dashboard.app")
    mod = None
    last_err = None
    for name in candidates:
        try:
            mod = importlib.import_module(name)
            break
        except Exception as e:
            last_err = e
            mod = None

    if mod is None:
        # Fallback mini web
        from flask import Flask, redirect
        mini = Flask("mini-web")
        try:
            _bind_admin_login(mini)
        except Exception:
            pass

        @mini.route("/")
        def _root():
            return redirect("/admin/login", 302)

        mini.run(host="0.0.0.0", port=port)
        return

    app = getattr(mod, "app", None)
    socketio = getattr(mod, "socketio", None)
    if app is None:
        from flask import Flask, redirect
        mini = Flask("mini-web")
        try:
            _bind_admin_login(mini)
        except Exception:
            pass

        @mini.route("/")
        def _root():
            return redirect("/admin/login", 302)

        mini.run(host="0.0.0.0", port=port)
        return

    # Bind login fallback ke dashboard utama
    try:
        _bind_admin_login(app)
    except Exception:
        pass

    if socketio is not None:
        try:
            socketio.run(app, host="0.0.0.0", port=port)
        except TypeError:
            socketio.run(app, host="0.0.0.0", port=port)
    else:
        app.run(host="0.0.0.0", port=port)

