# main.py — SatpamBot (hardened for Render) — 2025-08-15
from __future__ import annotations

import os
import gc
import signal
import logging
import asyncio
import importlib
from typing import Optional, Any

# ---------- logging ----------
def setup_logging() -> logging.Logger:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    log = logging.getLogger("SatpamBot")
    logging.getLogger("werkzeug").setLevel(logging.INFO)
    logging.getLogger("engineio").setLevel(logging.WARNING)
    logging.getLogger("socketio").setLevel(logging.WARNING)
    return log

log = setup_logging()

# ---------- helpers ----------
def env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}

def get_port() -> int:
    try:
        return int(os.getenv("PORT", "10000"))
    except Exception:
        return 10000

def get_token() -> str:
    for k in ("DISCORD_TOKEN", "BOT_TOKEN", "DISCORD_BOT_TOKEN"):
        val = os.getenv(k, "").strip()
        if val:
            return val
    raise RuntimeError("ENV DISCORD_TOKEN / BOT_TOKEN tidak diset")

async def preflight_gateway_ok(timeout: float = 8.0) -> bool:
    # cek cepat ke Discord API sebelum start bot
    try:
        import aiohttp  # lazy import
        async with aiohttp.ClientSession() as s:
            async with s.get("https://discord.com/api/v10/gateway", timeout=timeout) as r:
                return r.status == 200
    except Exception:
        return True  # kalau gagal cek, jangan blokir start

# ---------- web ----------
def import_web_app():
    try:
        mod = importlib.import_module("app")
        return getattr(mod, "app", None), getattr(mod, "socketio", None)
    except Exception as e:
        log.warning("app.py tidak bisa diimport: %s", e)
        return None, None

def build_mini_app():
    from flask import Flask, jsonify
    app = Flask("mini-web")
    state = {"ready": False}

    @app.get("/")
    def root():
        return "ok", 200

    @app.get("/healthz")
    def healthz():
        return jsonify({"ok": True, "bot_ready": state["ready"]}), 200

    @app.get("/ping")
    def ping():
        return "pong", 200

    @app.get("/bot_ready")
    def bot_ready():
        return jsonify({"ready": state["ready"]}), 200

    # <- tambahan sesuai permintaan
    @app.get("/callback")
    def callback():
        # tempatkan logic OAuth/webhook ringan di sini bila dibutuhkan
        return "ok", 200

    return app, state

def run_web(app, socketio=None, host="0.0.0.0", port: int = 10000):
    if socketio is not None:
        log.info("Starting web (socketio) on %s:%s", host, port)
        socketio.run(app, host=host, port=port, allow_unsafe_werkzeug=True)
    else:
        log.info("Starting web (flask) on %s:%s", host, port)
        app.run(host=host, port=port, use_reloader=False)

# ---------- bot ----------
def import_bot_module():
    mod = importlib.import_module("modules.discord_bot.discord_bot")
    return importlib.reload(mod)

async def run_bot(shared_app=None, ready_flag: Optional[dict] = None):
    import inspect

    token = get_token()
    start_delay = float(os.getenv("BOT_START_DELAY", "0") or 0)
    if start_delay > 0:
        log.info("Menunggu %.1fs (BOT_START_DELAY)...", start_delay)
        await asyncio.sleep(start_delay)

    if not await preflight_gateway_ok():
        log.warning("Preflight Discord gagal; coba lagi 5s...")
        await asyncio.sleep(5)

    mod = import_bot_module()

    # inject Flask app jika modul bot mengekspose setter
    if shared_app is not None:
        set_flask_app = getattr(mod, "set_flask_app", None)
        if callable(set_flask_app):
            try:
                set_flask_app(shared_app)
                log.info("Flask app dihubungkan ke modul bot.")
            except Exception as e:
                log.warning("set_flask_app error: %s", e)

    # prefer run_bot() bila ada
    run_fn = getattr(mod, "run_bot", None)
    if callable(run_fn):
        log.info("Menjalankan bot via run_bot()...")
        params_len = len(inspect.signature(run_fn).parameters)
        if inspect.iscoroutinefunction(run_fn):
            await (run_fn() if params_len == 0 else run_fn(token))  # type: ignore
        else:
            # fungsi sync
            await (asyncio.to_thread(run_fn) if params_len == 0 else asyncio.to_thread(run_fn, token))  # type: ignore
        return

    # fallback ke bot.start()
    bot = getattr(mod, "bot", None)
    if bot is None:
        raise RuntimeError("modules.discord_bot.discord_bot tidak punya run_bot() atau bot")

    async def mark_ready():
        if hasattr(bot, "wait_until_ready"):
            try:
                await bot.wait_until_ready()
                if ready_flag is not None:
                    ready_flag["ready"] = True
                    log.info("Bot READY.")
            except Exception:
                pass

    log.info("Menjalankan bot via bot.start()...")
    await asyncio.gather(mark_ready(), bot.start(token))  # type: ignore

async def supervise_bot(start_coro_factory, *, min_backoff=3, max_backoff=60):
    """Auto-restart kalau bot crash. Aktifkan dengan ENV BOT_SUPERVISE=1."""
    backoff = min_backoff
    while True:
        try:
            await start_coro_factory()
            log.info("Bot selesai (exit normal). Restart 5s...")
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception("Bot crash: %s", e)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)

# ---------- orchestrator ----------
def main():
    mode = os.getenv("MODE", "bot").strip().lower()
    if mode in {"minibot", "mini-bot"}:
        mode = "botmini"

    log.info("🌐 Mode: %s", mode)
    host = os.getenv("HOST", "0.0.0.0")
    port = get_port()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def on_signal(*_):
        log.info("Signal diterima, shutdown...")
        # biarkan tugas dibatalkan di finally
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, on_signal)
        except Exception:
            pass

    async def run_mode():
        web_app, socketio = (None, None)
        if mode in {"web", "both"}:
            web_app, socketio = import_web_app()
            if web_app is None:
                log.warning("app.py tidak ditemukan, pakai mini web.")
                web_app, _ = build_mini_app()

        if mode == "botmini":
            mini_app, ready = build_mini_app()
            web_task = asyncio.to_thread(lambda: mini_app.run(host=host, port=port, use_reloader=False))
            bot_coro_factory = (lambda: run_bot(shared_app=None, ready_flag=ready))
            if env_bool("BOT_SUPERVISE", False):
                await asyncio.gather(web_task, supervise_bot(bot_coro_factory))
            else:
                await asyncio.gather(web_task, bot_coro_factory())
            return

        if mode == "web":
            run_web(web_app, socketio, host=host, port=port)  # type: ignore
            return

        if mode == "bot":
            bot_coro_factory = (lambda: run_bot(shared_app=None))
            if env_bool("BOT_SUPERVISE", False):
                await supervise_bot(bot_coro_factory)
            else:
                await bot_coro_factory()
            return

        if mode == "both":
            assert web_app is not None
            web_runner = asyncio.to_thread(lambda: run_web(web_app, socketio, host=host, port=port))  # type: ignore
            bot_coro_factory = (lambda: run_bot(shared_app=web_app))
            if env_bool("BOT_SUPERVISE", False):
                await asyncio.gather(web_runner, supervise_bot(bot_coro_factory))
            else:
                await asyncio.gather(web_runner, bot_coro_factory())
            return

        log.warning("MODE '%s' tidak dikenal. Default ke 'bot'.", mode)
        await run_bot(shared_app=None)

    try:
        loop.run_until_complete(run_mode())
    finally:
        try:
            for t in asyncio.all_tasks(loop):
                t.cancel()
        except Exception:
            pass
        gc.collect()

if __name__ == "__main__":
    main()
