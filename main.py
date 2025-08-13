# SatpamBot/main.py
from __future__ import annotations

import os
import logging
import asyncio
import random

# (opsional) batasi koneksi HTTP discord.py biar "kalem" di free tier
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

# ---- filter agar /healthz & /ping tidak spam di log werkzeug ----
class _NoHealthz(logging.Filter):
    def filter(self, record):
        try:
            msg = record.getMessage()
        except Exception:
            return True
        for path in ("/healthz", "/ping"):
            if (f'"GET {path} ' in msg) or (f'"HEAD {path} ' in msg) or (path in msg):
                return False
        return True

# ---------------- Helpers ----------------
CF_HINTS = (
    "Error 1015",
    "Access denied | discord.com",
    "cf-error-details",
    "cdn-cgi/challenge",
    "You are being rate limited",
)

class PreflightError(Exception):
    """Soft failure: gateway check not healthy."""

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

def _get_bot():
    from modules.discord_bot.discord_bot import bot  # type: ignore
    return bot

async def _preflight_gateway_ok(timeout: float = 8.0) -> bool:
    if aiohttp is None:
        return True
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://discord.com/api/v10/gateway", timeout=timeout) as r:
                return r.status == 200
    except Exception:
        return True

async def _safe_close_bot():
    try:
        bot = _get_bot()
        await bot.close()
    except Exception:
        pass

# ---------------- Web (Flask) ----------------
def run_web() -> None:
    from app import app, bootstrap  # lokal project

    try:
        bootstrap()
        log.info("bootstrap: OK")
    except Exception as e:
        log.warning("bootstrap error: %s", e)

    # Route ping untuk UptimeRobot
    try:
        from flask import Response
        @app.route("/ping")
        def _ping():
            return Response("pong", mimetype="text/plain")
    except Exception:
        pass

    logging.getLogger("werkzeug").addFilter(_NoHealthz())

    port = int(os.getenv("PORT", "10000"))
    log.info("Starting web on :%s", port)
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)

# ---------------- Discord Bot ----------------
async def _start_bot_async() -> None:
    bot = _get_bot()
    token = _get_token()

    if aiohttp is not None:
        try:
            bot.http.connector = aiohttp.TCPConnector(
                limit=4, limit_per_host=2, ttl_dns_cache=300
            )
        except Exception:
            pass

    # Preflight opsional: matikan dengan DISABLE_PREFLIGHT=1
    if os.getenv("DISABLE_PREFLIGHT") != "1":
        ok = await _preflight_gateway_ok()
        if not ok:
            raise PreflightError("Gateway preflight failed")

    await bot.start(token)

async def bot_runner() -> None:
    from discord.errors import HTTPException

    tries = 0
    # Initial jitter sekali di awal (hindari tabrakan IP shared)
    await asyncio.sleep(random.randint(5, 20))

    while True:
        try:
            await _start_bot_async()
            break
        except PreflightError as e:
            await _safe_close_bot()
            tries += 1
            base = 60 * (2 ** min(tries - 1, 4))             # 60..960s
            sleep_s = min(900, base + random.randint(0, 30)) # cap 15m
            log.warning("[status] %s. Backoff %ss (try %s).", e, sleep_s, tries)
            await asyncio.sleep(sleep_s)
            continue
        except HTTPException as e:
            body = getattr(e, "text", "") or ""
            is_cf = (getattr(e, "status", None) == 429) and any(h in body for h in CF_HINTS)
            await _safe_close_bot()
            if is_cf:
                tries += 1
                base = 60 * (2 ** min(tries - 1, 4))             # cap ~16m
                sleep_s = min(900, base + random.randint(0, 30)) # cap 15m
                log.warning("[status] 429/Cloudflare. Backoff %ss (try %s).", sleep_s, tries)
                await asyncio.sleep(sleep_s)
                continue
            log.exception("[status] HTTPException status=%s; retry 30s", getattr(e, "status", "?"))
            await asyncio.sleep(30)
        except Exception:
            await _safe_close_bot()
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
            web_task = asyncio.create_task(asyncio.to_thread(run_web))
            bot_task = asyncio.create_task(bot_runner())
            await asyncio.gather(web_task, bot_task)

        asyncio.run(orchestrate())
        return

    log.warning("MODE tidak dikenal: %s. Default ke 'bot'.", mode)
    asyncio.run(bot_runner())

if __name__ == "__main__":
    main()
