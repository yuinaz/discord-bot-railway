# SatpamBot/main.py
from __future__ import annotations

import os
import logging
import asyncio

# aiohttp hanya dipakai untuk batasi koneksi HTTP (optional)
try:
    import aiohttp  # type: ignore
except Exception:
    aiohttp = None  # type: ignore

# ---------------- Logging ----------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
log = logging.getLogger("startup")

# ---------------- Helpers ----------------
CF_HINTS = (
    "Error 1015",
    "Access denied | discord.com",
    "cf-error-details",
    "cdn-cgi/challenge",
    "You are being rate limited",
)

def _get_token() -> str:
    token = (
        os.getenv("DISCORD_TOKEN")
        or os.getenv("BOT_TOKEN")
        or os.getenv("DISCORD_BOT_TOKEN")
        or os.getenv("DISCORD_BOT_TOKEN_LOCAL")
        or ""
    )
    if not token:
        raise RuntimeError("DISCORD_TOKEN / BOT_TOKEN / DISCORD_BOT_TOKEN tidak diset")
    return token

# ---------------- Web (Flask) ----------------
def run_web() -> None:
    """
    Jalankan web server. Di sini kita PANGGIL bootstrap() lebih dulu
    agar DB/config siap ketika service naik.
    """
    from app import app, bootstrap  # lokal ke project

    try:
        bootstrap()  # init DB + config.json, aman jika dipanggil berulang
        log.info("bootstrap: OK")
    except Exception as e:
        log.warning("bootstrap error: %s", e)

    port = int(os.getenv("PORT", "10000"))
    log.info("Starting web on :%s", port)
    # Matikan reloader agar tidak spawn proses dobel
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)

# ---------------- Discord Bot ----------------
async def _start_bot_async() -> None:
    from modules.discord_bot.discord_bot import bot  # lokal ke project

    token = _get_token()
    # Tweak konektor HTTP biar "kalem" (cocok free tier)
    if aiohttp is not None:
        try:
            bot.http.connector = aiohttp.TCPConnector(limit=8, limit_per_host=4, ttl_dns_cache=300)
        except Exception:
            pass

    await bot.start(token)

async def bot_runner() -> None:
    from discord.errors import HTTPException  # import saat runtime

    tries = 0
    while True:
        try:
            await _start_bot_async()
            break  # keluar normal
        except HTTPException as e:
            body = getattr(e, "text", "") or ""
            is_cf = (getattr(e, "status", None) == 429) and any(h in body for h in CF_HINTS)
            if is_cf:
                tries += 1
                # Exponential backoff: 1m → 2m → 4m → 8m → 16m → 32m (maks 60m)
                sleep_s = min(3600, 60 * (2 ** min(tries, 5)))
                log.error("[status] Cloudflare 1015/429 terdeteksi. Backoff %ss (try %s).", sleep_s, tries)
                await asyncio.sleep(sleep_s)
                continue
            log.exception("[status] HTTPException status=%s; retry 30s", getattr(e, "status", "?"))
            await asyncio.sleep(30)
        except Exception:
            log.exception("[status] Bot crashed; retry 30s")
            await asyncio.sleep(30)

# ---------------- Orchestrator ----------------
def main() -> None:
    mode = os.getenv("MODE", "bot").lower()
    log.info("Mode: %s", mode)

    if mode == "web":
        run_web()
        return

    if mode == "bot":
        asyncio.run(bot_runner())
        return

    if mode == "both":
        async def orchestrate():
            # Jalankan web di thread terpisah supaya bot tetap di event loop utama
            web_task = asyncio.create_task(asyncio.to_thread(run_web))
            bot_task = asyncio.create_task(bot_runner())
            await asyncio.gather(web_task, bot_task)

        asyncio.run(orchestrate())
        return

    # fallback jika MODE tidak dikenal
    log.warning("MODE tidak dikenal: %s. Default ke 'bot'.", mode)
    asyncio.run(bot_runner())

if __name__ == "__main__":
    main()
