import os, sys, threading, importlib, asyncio, inspect

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Support monorepo layout: allow importing from /satpambot
sys.path.append(os.path.join(BASE_DIR, "satpambot"))

def try_start_bot():
    # Only start if MODE allows and token exists
    mode = os.getenv("MODE", "both").lower()
    if mode not in ("both", "bot", "botmini"):
        print(f"[INFO] MODE={mode} -> bot disabled")
        return
    token = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")
    if not token:
        print("[INFO] BOT_TOKEN/DISCORD_TOKEN not set -> skip bot")
        return

    def _run():
        try:
            # Try multiple known entrypoints
            candidates = [
                os.getenv("BOT_ENTRY"),  # explicit override
                "satpambot.bot.main",
                "satpambot.bot.__main__",
                "modules.discord_bot.discord_bot",  # legacy
                "bot.main",
                "modules.discord_bot.__main__",
            ]
            candidates = [c for c in candidates if c]
            if not candidates:
                candidates = ["satpambot.bot.main", "modules.discord_bot.discord_bot", "bot.main"]
            for mod_name in candidates:
                try:
                    mod = importlib.import_module(mod_name)
                    # choose function
                    fn_name = os.getenv("BOT_FUNC", "").strip() or None
                    fns = [fn_name] if fn_name else ["main", "run_bot", "run", "start"]
                    for fn in fns:
                        if not fn or not hasattr(mod, fn):
                            continue
                        func = getattr(mod, fn)
                        if inspect.iscoroutinefunction(func):
                            return asyncio.run(func())
                        res = func()
                        if inspect.iscoroutine(res):
                            return asyncio.run(res)
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
                    await asyncio.to_thread(_run)
                    return
                except Exception as e:
                    print("[ERROR] Bot crash:", e)
                    await asyncio.sleep(delay)
        threading.Thread(target=lambda: asyncio.run(supervise_loop()), daemon=True).start()
    else:
        threading.Thread(target=_run, daemon=True).start()

def serve_dashboard():
    mode = os.getenv("MODE", "both").lower()
    # Try SocketIO app first
    for mod_name, sock_attr, app_attr in [
        ("app", "socketio", "app"),  # root shim (we ship this)
        ("dashboard.app", "socketio", "app"),
        ("satpambot.dashboard.app", "socketio", "app"),
        ("app", None, "app"),        # plain Flask fallback
        ("dashboard.app", None, "app"),
        ("satpambot.dashboard.app", None, "app"),
    ]:
        try:
            mod = importlib.import_module(mod_name)
            app = getattr(mod, app_attr)
            port = int(os.getenv("PORT", "10000"))
            if sock_attr and hasattr(mod, sock_attr):
                sock = getattr(mod, sock_attr)
                try:
                    sock.run(app, host="0.0.0.0", port=port)
                    return
                except Exception:
                    pass
            try:
                app.add_url_rule("/ping", "ping", lambda: ("ok", 200))
            except Exception:
                pass
            app.run(host="0.0.0.0", port=port)
            return
        except Exception as e:
            continue

    # Last resort: tiny Flask so /ping works
    from flask import Flask
    mini = Flask("mini-web")
    @mini.get("/ping")
    def ping(): return "ok", 200
    port = int(os.getenv("PORT", "10000"))
    mini.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    try_start_bot()
    serve_dashboard()
