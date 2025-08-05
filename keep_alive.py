from threading import Thread
from flask import Flask

def start_keep_alive():
    app = Flask('keep_alive')

    @app.route('/')
    def home():
        return "🛡️ SatpamBot Monitor is alive!", 200

    def run():
        app.run(host='0.0.0.0', port=9090)  # ⬅️ Gunakan port berbeda agar tidak bentrok

    t = Thread(target=run)
    t.daemon = True
    t.start()

# Jangan biarkan keep_alive.py dijalankan langsung
if __name__ == "__main__":
    print("⚠️ Jangan jalankan file ini langsung. Jalankan lewat main.py.")
