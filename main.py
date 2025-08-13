import os
import logging
import asyncio
import aiohttp
from typing import Optional

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
log = logging.getLogger("startup")

def get_web_app():
    from app import app  # lokal
    return app

def get_bot():
    from modules.discord_bot.discord_bot import bot  # lokal
    return bot

def get_token() -> Optional[str]:
    return (
        os.getenv("DISCORD_TOKEN")
        or os.getenv("BOT_TOKEN")
        or os.getenv("DISCORD_BOT_TOKEN")
        or os.getenv("DISCORD_BOT_TOKEN_LOCAL")
    )

CF_HINTS = (
    "Error 1015",
    "Access denied | discord.com",
    "cf-error-details",
    "cdn-cgi/challenge",
    "You are being rate limited",
)

async def start_bot_async():
    token = get_token()
    if not token:
        raise RuntimeError("DISCORD_TOKEN / BOT_TOKEN tidak diset")
    bot = get_bot()
    # Biar lebih “kalem” di free plan
    try:
        bot.http.connector = aiohttp.TCPConnector(limit=8, limit_per_host=4, ttl_dns_cache=300)
    except Exception:
        pass
    await bot.start(token)

async def bot_runner():
    from discord.errors import HTTPException
    tries = 0
    while True:
        try:
            await start_bot_async()
            break  # keluar normal
        except HTTPException as e:
            body = getattr(e, "text", "") or ""
            is_cf = (e.status == 429) and any(h in body for h in CF_HINTS)
            if is_cf:
                tries += 1
                # Exponential backoff: 1m → 2m → 4m → 8m → 16m → 32m (max 60m)
                sleep_s = min(3600, 60 * (2 ** min(tries, 5)))
                log.error("[status] Cloudflare 1015/429 terdeteksi. Backoff %ss (try %s).", sleep_s, tries)
                await asyncio.sleep(sleep_s)
                continue
            log.exception("[status] HTTPException status=%s; retry 30s", getattr(e, "status", "?"))
            await asyncio.sleep(30)
        except Exception:
            log.exception("[status] Bot crashed; retry 30s")
            await asyncio.sleep(30)

def run_web():
    app = get_web_app()
    # Health check agar Render nggak restart2
    try:
        from flask import Response
        @app.route("/healthz")
        def _healthz():
            return Response("ok", mimetype="text/plain")
    except Exception:
        pass
    port = int(os.getenv("PORT", "10000"))
    log.info("Starting web on :%s", port)
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)

def main():
    mode = os.getenv("MODE", "bot").lower()
    log.info("Mode: %s", mode)
    if mode == "bot":
        asyncio.run(bot_runner())
    elif mode == "web":
        run_web()
    elif mode == "both":
        async def orchestrate():
            web_task = asyncio.create_task(asyncio.to_thread(run_web))
            bot_task = asyncio.create_task(bot_runner())
            await asyncio.gather(web_task, bot_task)
        asyncio.run(orchestrate())
    else:
        log.warning("MODE tidak dikenal: %s. Default ke 'bot'.", mode)
        asyncio.run(bot_runner())

if __name__ == "__main__":
    main()
