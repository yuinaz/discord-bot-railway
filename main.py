# Entry runner - keep config intact, ensure WEB starts (and responds) BEFORE loading cogs/bot.
from __future__ import annotations

# Keep hooks/banner from sitecustomize (no separate server will be started)
try:
    import sitecustomize  # noqa: F401
except Exception as _e:
    print(f"[sitecustomize] note: {_e}", flush=True)

import os
import threading
import logging
import time
import http.client

log = logging.getLogger("entry.main")

def _serve_web():
    from app import create_app
    app = create_app()
    log.info("[web] Flask app created via create_app()")
    port = int(os.environ.get("PORT", "10000"))
    log.info("🌐 Serving web on 0.0.0.0:%s", port)
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

def _wait_web_ready(port: int, timeout: float = 30.0) -> bool:
    # Wait until the real app answers HEAD /healthz (fallback HEAD /)
    deadline = time.time() + timeout
    while time.time() < deadline:
        for path in ("/healthz", "/"):
            try:
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1.0)
                conn.request("HEAD", path)
                resp = conn.getresponse()
                if resp and resp.status in (200, 301, 302, 307, 308):
                    return True
            except Exception:
                pass
        time.sleep(0.25)
    return False

def main():
    # Start WEB in background thread
    t = threading.Thread(target=_serve_web, name="web-serve", daemon=True)
    t.start()

    # Ensure WEB is ready before starting BOT (so logs show app first)
    port = int(os.environ.get("PORT", "10000"))
    _wait_web_ready(port)

    # Now run the Discord bot (cogs will load after web is up)
    from satpambot.bot.modules.discord_bot.discord_bot import run_bot as _run
    return _run()

if __name__ == "__main__":
    main()
