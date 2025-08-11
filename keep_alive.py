import os
from threading import Thread
from flask import Flask

def start_keep_alive():
    """Start a tiny HTTP server if KEEP_ALIVE=1 (for uptime pings)."""
    if os.getenv("KEEP_ALIVE") != "1":
        return
    app = Flask('keep_alive')

    @app.route('/')
    def home():
        return "🛡️ SatpamBot Monitor is alive!", 200

    def run():
        app.run(host='0.0.0.0', port=int(os.getenv("KEEP_ALIVE_PORT","9090")), threaded=True)

    t = Thread(target=run, daemon=True)
    t.start()

# prevent direct execution
if __name__ == "__main__":
    print("⚠️ Jangan jalankan file ini langsung. Dipanggil dari main/bot.")
