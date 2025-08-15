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

def serve_dashboard():
    for mod_name, sock_attr, app_attr in [
        ("app", "socketio", "app"),
        ("dashboard.app", "socketio", "app"),
        ("satpambot.dashboard.app", "socketio", "app"),
        ("app", None, "app"),
        ("dashboard.app", None, "app"),
        ("satpambot.dashboard.app", None, "app"),
    ]:
        try:
            mod = importlib.import_module(mod_name)
            app = getattr(mod, app_attr)
            port = int(os.getenv("PORT", "10000"))
            if sock_attr and hasattr(mod, sock_attr):
                sock = getattr(mod, sock_attr)
                try: sock.run(app, host="0.0.0.0", port=port, request_handler=NoPingWSGIRequestHandler); return
                except Exception: pass
            try: app.add_url_rule("/ping", "ping", lambda: ("ok", 200))
            except Exception: pass
            app.run(host="0.0.0.0", port=port, request_handler=NoPingWSGIRequestHandler); return
        except Exception: continue
    from flask import Flask
    mini = Flask("mini-web")
    @mini.get("/ping")
    def ping(): return "ok", 200
    port = int(os.getenv("PORT", "10000"))
    mini.run(host="0.0.0.0", port=port, request_handler=NoPingWSGIRequestHandler)

if __name__ == "__main__":
    ensure_dirs(); try_start_bot(); serve_dashboard()
