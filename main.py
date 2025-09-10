# Single-process runner for Render Free plan
# - Starts Flask web (serves /uptime, /healthz) on PORT
# - Runs Discord bot in a resilient restart loop (no ENV needed)
from __future__ import annotations

import os, threading, time, logging, http.client, traceback

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("entry.main")

def _serve_web():
    # Import here to avoid side effects at module import time
    from app import app  # app = create_app()
    port = int(os.environ.get("PORT", "10000"))
    log.info("🌐 Serving web on 0.0.0.0:%s", port)
    # Use Flask's built-in server; do NOT enable reloader in production
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

def _wait_web_ready(port: int, retries: int = 30, delay: float = 0.5):
    for _ in range(retries):
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1.5)
            conn.request("GET", "/uptime")
            resp = conn.getresponse()
            if resp.status == 200:
                return True
        except Exception:
            pass
        time.sleep(delay)
    return False

def _run_bot_once():
    # Import late to ensure web has started (and any sitecustomize hooks ran)
    from satpambot.bot.modules.discord_bot.discord_bot import run_bot
    run_bot()

def main():
    # 1) Start web in a background thread
    t = threading.Thread(target=_serve_web, name="web-serve", daemon=True)
    t.start()

    # 2) Wait until web is actually serving /uptime
    port = int(os.environ.get("PORT", "10000"))
    if not _wait_web_ready(port):
        log.warning("Web not ready after wait; continuing anyway.")
    else:
        log.info("Web is ready on port %s", port)

    # 3) Resilient bot loop
    backoff = 5  # seconds; doubles up to 60s
    while True:
        try:
            log.info("🤖 Starting Discord bot...")
            _run_bot_once()
            log.warning("Bot returned gracefully; restarting in 3s...")
            time.sleep(3)
            backoff = 5  # reset on clean exit
        except Exception as e:
            log.error("Bot crashed: %s\n%s", e, traceback.format_exc())
            log.info("Restarting in %ss...", backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)

if __name__ == "__main__":
    main()
