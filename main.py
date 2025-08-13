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
    # satu-satunya sumber bot (module-level object)
    from modules.discord_bot.discord_bot import bot  # type: ignore
    return bot

async def _preflight_gateway_ok(timeout: float = 8.0) -> bool:
    """Cek cepat gateway Discord; kalau tidak 200, tunda start agar tidak memicu 1015."""
    if aiohttp is None:
        return True
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://discord.com/api/v10/gateway", timeout=timeout) as r:
                return r.status == 200
    except Exception:
        # kalau ada error jaringan, biarkan bot.start() yang handle
        return True

async def _safe_close_bot():
    """Tutup session aiohttp milik discord.py agar tidak ada 'Unclosed client session'."""
    try:
        bot = _get_bot()
        await bot.close()
    except Exception:
        pass

# ---------------- Web (Flask) ----------------
def run_web() -> None:
    """
    Jalankan web server. Panggil bootstrap() lebih dulu agar DB/config siap.
    Nonaktifkan log /healthz & /ping agar tidak spam di Render.
    """
    from app import app, bootstrap  # lokal project

    try:
        bootstrap()  # init DB + config.json (idempotent)
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

    # Pasang filter anti-spam untuk akses /healthz & /ping
    logging.getLogger("werkzeug").addFilter(_NoHealthz())

    port = int(os.getenv("PORT", "10000"))
    log.info("Starting web on :%s", port)
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)

# ---------------- Discord Bot ----------------
async def _start_bot_async() -> None:
    bot = _get_bot()
    token = _get_token()

    # Tweak konektor HTTP biar "kalem" (cocok free tier)
    if aiohttp is not None:
        try:
            bot.http.connector = aiohttp.TCPConnector(
                limit=8, limit_per_host=4, ttl_dns_cache=300
            )
        except Exception:
            pass

    # Preflight ringan untuk menghindari start saat gateway lagi tidak bisa
    ok = await _preflight_gateway_ok()
    if not ok:
        raise RuntimeError("Gateway preflight failed")

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
            # pastikan session lama ditutup agar tidak ada 'Unclosed client session'
            await _safe_close_bot()
            if is_cf:
                tries += 1
                # Exponential backoff: 60s,120s,240s,480s,960s,1920s (cap 3600) + jitter 0–30s
                base = 60 * (2 ** min(tries - 1, 5))
                sleep_s = min(3600, base + random.randint(0, 30))
                log.error("[status] Cloudflare 1015/429 terdeteksi. Backoff %ss (try %s).", sleep_s, tries)
                await asyncio.sleep(sleep_s)
                continue
            log.exception("[status] HTTPException status=%s; retry 30s", getattr(e, "status", "?"))
            await asyncio.sleep(30)
        except Exception:
            # tutup session pada error umum juga
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
