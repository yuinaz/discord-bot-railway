import os, sys, threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, "satpambot"))

# Jalankan Discord bot di thread terpisah (import side-effect start)
def start_bot():
    try:
        os.environ.setdefault("MODE", "production")
        __import__("satpambot.bot.main")
    except Exception as e:
        print("[WARN] Bot tidak start:", e)

try:
    from satpambot.dashboard.app import app, socketio
    threading.Thread(target=start_bot, daemon=True).start()
    port = int(os.getenv("PORT", "10000"))
    try:
        socketio.run(app, host="0.0.0.0", port=port)
    except Exception:
        app.run(host="0.0.0.0", port=port)
except ImportError as e:
    print("[FATAL] Gagal import dashboard:", e)
    raise
