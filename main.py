import os, sys, threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Tambahkan /satpambot ke sys.path agar bisa import "dashboard" dan "satpambot.bot"
sys.path.append(os.path.join(BASE_DIR, "satpambot"))

def start_bot():
    """Jalankan Discord bot di thread terpisah (opsional)."""
    try:
        # Coba beberapa entrypoint yang umum
        import importlib
        for mod_name in ("satpambot.bot.main", "satpambot.bot.__main__"):
            try:
                mod = importlib.import_module(mod_name)
                if hasattr(mod, "main"):
                    mod.main()
                    return
                if hasattr(mod, "run_bot"):
                    mod.run_bot()
                    return
            except Exception:
                continue
        # Fallback: import side-effect
        __import__("satpambot.bot.main")
    except Exception as e:
        print("[WARN] Bot tidak start:", e)

if os.getenv("RUN_BOT", "1") != "0":
    threading.Thread(target=start_bot, daemon=True).start()

try:
    # Utama: dashboard Flask (dengan/atau tanpa SocketIO)
    from dashboard.app import app, socketio  # type: ignore
    port = int(os.getenv("PORT", "10000"))
    try:
        socketio.run(app, host="0.0.0.0", port=port)  # type: ignore
    except Exception:
        app.run(host="0.0.0.0", port=port)
except ImportError:
    # Jika tidak ada socketio
    from dashboard.app import app  # type: ignore
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
