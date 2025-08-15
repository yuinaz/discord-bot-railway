import os, sys, threading, importlib, asyncio, inspect

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# support monorepo: import dari /satpambot kalau ada
sys.path.append(os.path.join(BASE_DIR, "satpambot"))

def try_start_bot():
    # 1) Hormati RUN_BOT
    if os.getenv("RUN_BOT", "1") == "0":
        print("[INFO] RUN_BOT=0 → skip start bot")
        return

    # 2) Wajib ada token
    token = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")
    if not token:
        print("[INFO] Skip start bot: BOT_TOKEN/DISCORD_TOKEN tidak diset")
        return

    # 3) Cari entrypoint umum
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
                    try:
                        # dukung async & sync
                        if inspect.iscoroutinefunction(func):
                            asyncio.run(func())
                        else:
                            res = func()
                            if inspect.iscoroutine(res):
                                asyncio.run(res)
                        print(f"[INFO] Bot started via {mod_name}.{fn}")
                        return
                    except Exception as e:
                        print(f"[WARN] {mod_name}.{fn} gagal: {e}")
                        continue
            # fallback: import side-effect
            try:
                importlib.import_module(mod_name)
                print(f"[INFO] Bot imported (side-effect): {mod_name}")
                return
            except Exception:
                pass
        except Exception:
            continue
    print("[INFO] Tidak menemukan entrypoint bot yang cocok; skip.")

def serve_dashboard():
    # Coba dashboard dengan SocketIO dulu
    for mod_name, sock_attr, app_attr in [
        ("dashboard.app", "socketio", "app"),
        ("satpambot.dashboard.app", "socketio", "app"),
        ("app", None, "app"),  # legacy root
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
            # Fallback: Flask biasa + /ping
            try:
                app.add_url_rule("/ping", "ping", lambda: ("ok", 200))
            except Exception:
                pass
            app.run(host="0.0.0.0", port=port)
            return
        except Exception:
            continue

    # Fallback terakhir: mini Flask supaya sehat di Render/UptimeRobot
    try:
        from flask import Flask
        app = Flask(__name__)
        @app.get("/ping")
        def ping(): return "ok", 200
        port = int(os.getenv("PORT", "10000"))
        app.run(host="0.0.0.0", port=port)
    except Exception as e:
        print("[FATAL] tidak ada app yang bisa dijalankan:", e)
        raise

if __name__ == "__main__":
    # Start bot di thread terpisah (kalau diizinkan & token ada)
    threading.Thread(target=try_start_bot, daemon=True).start()
    serve_dashboard()
