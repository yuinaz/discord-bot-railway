# SatpamBot/main.py
from __future__ import annotations

import os
import gc
import logging
import asyncio
import random
import importlib
import time
from typing import Optional

try:
    import aiohttp  # type: ignore
except Exception:
    aiohttp = None  # type: ignore

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
log = logging.getLogger("startup")

# ===== throttle log /ping (default 30 menit) =====
LOG_PING = os.getenv("LOG_PING", "0") == "1"
PING_LOG_INTERVAL = int(os.getenv("PING_LOG_INTERVAL", "1800"))  # detik; 1800 = 30 menit
_last_ping_log_ts = 0.0

# ===== state untuk /bot_ready =====
ACTIVE_BOT: Optional[object] = None

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

CF_HINTS = (
    "Error 1015",
    "Access denied | discord.com",
    "cf-error-details",
    "cdn-cgi/challenge",
    "You are being rate limited",
)

class PreflightError(Exception):
    pass

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

def _new_bot():
    import modules.discord_bot.discord_bot as dmod  # type: ignore
    dmod = importlib.reload(dmod)
    return dmod.bot

async def _preflight_gateway_ok(timeout: float = 8.0) -> bool:
    if aiohttp is None:
        return True
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://discord.com/api/v10/gateway", timeout=timeout) as r:
                return r.status == 200
    except Exception:
        return True

async def _force_close_http_session(bot):
    try:
        await bot.close()
    except Exception:
        pass
    try:
        http = getattr(bot, "http", None)
        sess = getattr(http, "_HTTPClient__session", None)
        if sess and hasattr(sess, "closed") and not sess.closed:
            await sess.close()
    except Exception:
        pass
    await asyncio.sleep(0)
    gc.collect()

# ---------------- Web routes helper ----------------
def _add_common_routes(app):
    from flask import Response, jsonify

    @app.route("/")
    def _root():
        return Response("ok", mimetype="text/plain")

    @app.route("/healthz")
    def _hz():
        return Response("ok", mimetype="text/plain")

    @app.route("/ping")
    def _ping():
        global _last_ping_log_ts
        if LOG_PING:
            now = time.monotonic()
            if now - _last_ping_log_ts >= PING_LOG_INTERVAL:
                logging.getLogger("startup").info("[keepalive] /ping received")
                _last_ping_log_ts = now
        return Response("pong", mimetype="text/plain")

    @app.route("/bot_ready")
    def _bot_ready():
        try:
            ready = bool(ACTIVE_BOT and getattr(ACTIVE_BOT, "is_ready")())
        except Exception:
            ready = False
        status = 200 if ready else 503
        return jsonify({"bot_ready": ready}), status

    @app.route("/callback")
    def _callback():
        # Callback sederhana untuk OAuth/Invite – cukup return 200
        return Response("ok", mimetype="text/plain")

# ---------------- Full web (dashboard) ----------------
def run_web() -> None:
    from app import app, bootstrap
    try:
        bootstrap(); log.info("bootstrap: OK")
    except Exception as e:
        log.warning("bootstrap error: %s", e)

    try:
        _add_common_routes(app)
    except Exception:
        pass

    logging.getLogger("werkzeug").addFilter(_NoHealthz())
    port = int(os.getenv("PORT", "10000"))
    log.info("Starting web on :%s", port)
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)

# ---------------- Mini web (untuk MODE=botmini) ----------------
def run_mini_web() -> None:
    """
    Mini HTTP server agar service bot dianggap Web Service di Render Free.
    Punya route: /, /ping, /healthz, /bot_ready, /callback
    """
    try:
        from flask import Flask
        app = Flask("mini")
        _add_common_routes(app)
        logging.getLogger("werkzeug").addFilter(_NoHealthz())
        port = int(os.getenv("PORT", "10000"))
        log.info("Starting mini web on :%s", port)
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)
        return
    except Exception:
        # fallback tanpa Flask
        import http.server, socketserver, json
        class Handler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                global ACTIVE_BOT, _last_ping_log_ts
                if self.path in ("/", "/healthz", "/ping", "/bot_ready", "/callback"):
                    if self.path == "/ping":
                        if LOG_PING:
                            now = time.monotonic()
                            if now - _last_ping_log_ts >= PING_LOG_INTERVAL:
                                logging.getLogger("startup").info("[keepalive] /ping received")
                                _last_ping_log_ts = now
                        body, status, ctype = b"pong", 200, "text/plain"
                    elif self.path == "/bot_ready":
                        try:
                            ready = bool(ACTIVE_BOT and getattr(ACTIVE_BOT, "is_ready")())
                        except Exception:
                            ready = False
                        body = json.dumps({"bot_ready": ready}).encode("utf-8")
                        status, ctype = (200 if ready else 503), "application/json"
                    else:
                        body, status, ctype = b"ok", 200, "text/plain"
                    self.send_response(status)
                    self.send_header("Content-Type", ctype)
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_error(404)
            def log_message(self, *args, **kwargs): pass
        port = int(os.getenv("PORT", "10000"))
        with socketserver.TCPServer(("", port), Handler) as httpd:
            log.info("Starting mini web on :%s", port)
            httpd.serve_forever()

# ---------------- Discord Bot ----------------
async def _start_bot_async(bot) -> None:
    token = _get_token()
    if aiohttp is not None:
        try:
            # Sedikit lebih longgar agar request /interactions tidak timeout,
            # tetap sopan untuk menghindari 429.
            connector = aiohttp.TCPConnector(
                limit=3,          # dari 1 -> 3
                limit_per_host=2, # dari 1 -> 2
                ttl_dns_cache=600
            )
            timeout = aiohttp.ClientTimeout(
                total=20, connect=10, sock_connect=10, sock_read=15
            )
            bot.http.connector = connector
            # pastikan session HTTPClient pakai connector & timeout ini
            http = getattr(bot, "http", None)
            sess = getattr(http, "_HTTPClient__session", None)
            if sess and not sess.closed:
                await sess.close()
            http._HTTPClient__session = aiohttp.ClientSession(  # type: ignore
                connector=connector, timeout=timeout
            )
        except Exception:
            pass
    if os.getenv("DISABLE_PREFLIGHT") != "1":
        ok = await _preflight_gateway_ok()
        if not ok:
            raise PreflightError("Gateway preflight failed")
    await bot.start(token)

async def bot_runner() -> None:
    from discord.errors import HTTPException
    global ACTIVE_BOT

    tries = 0
    # Delay awal (ENV) atau jitter kecil
    try:
        start_delay = int(os.getenv("BOT_START_DELAY", "").strip() or "0")
    except Exception:
        start_delay = 0
    if start_delay > 0:
        log.info("Delaying first login for %ss (BOT_START_DELAY).", start_delay)
        await asyncio.sleep(start_delay)
    else:
        await asyncio.sleep(random.randint(5, 15))

    while True:
        bot = _new_bot()
        ACTIVE_BOT = bot  # simpan untuk /bot_ready
        try:
            await _start_bot_async(bot)
            break  # keluar normal jika bot.stop() dipanggil
        except PreflightError as e:
            await _force_close_http_session(bot)
            tries += 1
            base = 60 * (2 ** min(tries - 1, 4))
            sleep_s = min(900, base + random.randint(0, 30))  # max 15m
            logging.warning("[status] %s. Backoff %ss (try %s).", e, sleep_s, tries)
            await asyncio.sleep(sleep_s)
            continue
        except HTTPException as e:
            body = getattr(e, "text", "") or ""
            is_cf = (getattr(e, "status", None) == 429) and any(h in body for h in CF_HINTS)
            await _force_close_http_session(bot)
            if is_cf:
                tries += 1
                base = 60 * (2 ** min(tries - 1, 4))
                sleep_s = min(900, base + random.randint(0, 30))
                logging.warning("[status] 429/Cloudflare. Backoff %ss (try %s).", sleep_s, tries)
                await asyncio.sleep(sleep_s)
                continue
            logging.exception("[status] HTTPException status=%s; retry 30s", getattr(e, "status", "?"))
            await asyncio.sleep(30)
        except Exception:
            await _force_close_http_session(bot)
            logging.exception("[status] Bot crashed; retry 30s")
            await asyncio.sleep(30)
        finally:
            # kalau belum ready, jangan pegang referensi supaya GC bersih
            try:
                ACTIVE_BOT = bot if getattr(bot, "is_ready")() else None
            except Exception:
                ACTIVE_BOT = None
            if ACTIVE_BOT is None:
                del bot
                gc.collect()

# ---------------- Orchestrator ----------------
def main() -> None:
    mode = os.getenv("MODE", "bot").lower()
    log.info("Mode: %s", mode)
    if mode == "web":
        run_web(); return
    if mode == "bot":
        asyncio.run(bot_runner()); return
    if mode == "both":
        async def orchestrate():
            web_task = asyncio.create_task(asyncio.to_thread(run_web))
            bot_task = asyncio.create_task(bot_runner())
            await asyncio.gather(web_task, bot_task)
        asyncio.run(orchestrate()); return
    if mode == "botmini":
        async def orchestrate_mini():
            web_task = asyncio.create_task(asyncio.to_thread(run_mini_web))
            bot_task = asyncio.create_task(bot_runner())
            await asyncio.gather(web_task, bot_task)
        asyncio.run(orchestrate_mini()); return
    log.warning("MODE tidak dikenal: %s. Default ke 'bot'.", mode)
    asyncio.run(bot_runner())

if __name__ == "__main__":
    main()
