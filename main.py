# Single-process runner for Render Free plan (web + bot)
# Uses shim_runner.start_bot (async). No ENV edits required.
from __future__ import annotations

import os, threading, time, logging, http.client, traceback, asyncio

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("entry.main")

def _serve_web():
    from app import app  # app = create_app()
    port = int(os.environ.get("PORT", "10000"))
    log.info("🌐 Serving web on 0.0.0.0:%s", port)
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

def _wait_web_ready(port: int, retries: int = 40, delay: float = 0.5):
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

async def _bot_once_async():
    try:
        from satpambot.bot.modules.discord_bot.shim_runner import start_bot
    except Exception:
        from satpambot.bot.modules.discord_bot.shim_runner import start_bot  # type: ignore
    await start_bot()

def main():
    t = threading.Thread(target=_serve_web, name="web-serve", daemon=True)
    t.start()

    port = int(os.environ.get("PORT", "10000"))
    if not _wait_web_ready(port):
        log.warning("Web not ready after wait; continuing anyway.")
    else:
        log.info("Web is ready on port %s", port)

    backoff = 5
    while True:
        try:
            log.info("🤖 Starting Discord bot (shim_runner.start_bot)...")
            asyncio.run(_bot_once_async())
            log.warning("Bot returned gracefully; restarting in 3s...")
            time.sleep(3)
            backoff = 5
        except Exception as e:
            log.error("Bot crashed: %s\n%s", e, traceback.format_exc())
            log.info("Restarting in %ss...", backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)

if __name__ == "__main__":
    main()
