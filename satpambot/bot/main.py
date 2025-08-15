from __future__ import annotations
import os, importlib, asyncio, logging, inspect

log = logging.getLogger(__name__)

def _should_run_bot() -> bool:
    v = (os.getenv("RUN_BOT") or "").strip().lower()
    if v in ("0","false","no","off"):  # explicit off
        return False
    if v in ("1","true","yes","on"):   # explicit on
        return True
    # AUTO: ada token -> run; tanpa token -> skip (web tetap hidup)
    return bool(os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN"))

def import_bot_module():
    # PRIORITAS: ENV override -> shim_runner (AMAN) -> modul lama (legacy)
    names = [
        os.getenv("DISCORD_BOT_MODULE") or "satpambot.bot.modules.discord_bot.shim_runner",
        "satpambot.bot.modules.discord_bot.discord_bot",
        "modules.discord_bot.discord_bot",
        "satpambot.bot.discord_bot",
        "satpambot.bot.discord_bot.main",
        "discord_bot.discord_bot",
    ]
    last = None
    for name in names:
        try:
            mod = importlib.import_module(name)
            log.info("[bot.main] imported %s", name)
            return mod, name
        except Exception as e:
            last = e
    raise ImportError("Tidak bisa import modul bot dari kandidat-kandidat") from last

async def run_once():
    mod, name = import_bot_module()
    # Cari entrypoint dan PASTIKAN di-await bila coroutine
    for attr in ("start_bot","run_bot","main","start"):
        if hasattr(mod, attr):
            fn = getattr(mod, attr)
            if inspect.iscoroutinefunction(fn):
                return await fn()
            res = fn()
            if inspect.iscoroutine(res):
                return await res
            return res
    # Fallback: modul expose .bot.start(token)
    bot = getattr(mod, "bot", None)
    token = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")
    if bot and token and hasattr(bot, "start"):
        start = getattr(bot, "start")
        if inspect.iscoroutinefunction(start):
            return await start(token)
        else:
            return await asyncio.to_thread(start, token)
    raise ImportError("Modul bot tidak punya entrypoint yang dikenali (start_bot/run_bot/main/start)")

async def supervise():
    while True:
        try:
            await run_once()
            return
        except Exception as e:
            log.error("bot supervise loop error: %s", e, exc_info=True)
            await asyncio.sleep(10)

def run_supervisor():
    if not _should_run_bot():
        log.info("[bot.main] AUTO: token tidak ada / RUN_BOT=0 -> skip bot (web-only)")
        return
    asyncio.run(supervise())
