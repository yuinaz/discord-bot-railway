import os, sys
from pathlib import Path

# Ensure project root (where app.py is) is on sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app, socketio

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    socketio.run(app, host="0.0.0.0", port=port)
