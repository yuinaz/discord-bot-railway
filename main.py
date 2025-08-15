import os, sys, threading, importlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# support monorepo: import dari /satpambot kalau ada
sys.path.append(os.path.join(BASE_DIR, "satpambot"))

def try_start_bot():
    # Coba beberapa entrypoint umum
    candidates = [
        "satpambot.bot.main",
        "satpambot.bot.__main__",
        "modules.discord_bot.discord_bot",   # legacy
        "bot.main",
        "modules.discord_bot.__main__",
    ]
    for mod_name in candidates:
        try:
            mod = importlib.import_module(mod_name)
            for fn in ("main", "run_bot", "run", "start"):
                if hasattr(mod, fn):
                    try:
                        getattr(mod, fn)()
                        return
                    except Exception as e:
                        print(f"[WARN] bot {mod_name}.{fn} gagal:", e)
                        # lanjut cari kandidat lain
            # fallback: import side-effect
            return
        except Exception:
            continue
    print("[INFO] Bot entrypoint tidak ditemukan; lewati start bot.")

def serve_dashboard():
    # Coba dengan SocketIO dulu, lalu fallback ke Flask biasa
    candidates = [
        ("dashboard.app", "socketio", "app"),
        ("satpambot.dashboard.app", "socketio", "app"),
        ("app", None, "app"),  # legacy root app.py
    ]
    for mod_name, sock_attr, app_attr in candidates:
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
            # Fallback: Flask biasa + /ping healthcheck
            try:
                app.add_url_rule("/ping", "ping", lambda: ("ok", 200))
            except Exception:
                pass
            app.run(host="0.0.0.0", port=port)
            return
        except Exception as e:
            continue
    # Ultimate fallback: minimal Flask supaya Render/UptimeRobot sehat
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

if os.getenv("RUN_BOT", "1") != "0":
    threading.Thread(target=try_start_bot, daemon=True).start()

if __name__ == "__main__":
    serve_dashboard()
