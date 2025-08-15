# Supervisor for Discord bot with env override + robust awaiting
from __future__ import annotations
import os, importlib, asyncio, logging, inspect

log = logging.getLogger(__name__)

def import_bot_module():
    # Candidate order: ENV override first, then common paths
    names = []
    envmod = os.getenv("DISCORD_BOT_MODULE")
    if envmod:
        names.append(envmod)
    names += [
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
    raise ImportError("Tidak bisa import modul bot") from last

async def run_once():
    mod, name = import_bot_module()
    # Find a start callable
    for attr in ("start_bot", "run_bot", "main", "start"):
        fn = getattr(mod, attr, None)
        if fn:
            if inspect.iscoroutinefunction(fn):
                return await fn()
            try:
                res = fn()
                if inspect.iscoroutine(res):
                    return await res
                return res
            except TypeError:
                # If requires args (unlikely), try calling without
                return await asyncio.to_thread(fn)
    # If module exposes a 'bot' with .start()
    bot = getattr(mod, "bot", None)
    token = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")
    if bot and token:
        start = getattr(bot, "start", None)
        if inspect.iscoroutinefunction(start):
            return await start(token)
    raise ImportError("Modul bot tidak punya start callable yang dikenali")

async def supervise():
    # retry loop instead of crashing the whole process
    while True:
        try:
            await run_once()
            return
        except Exception as e:
            log.error("bot supervise loop error: %s", e, exc_info=True)
            await asyncio.sleep(10)

def run_supervisor():
    # Default to RUN_BOT=0 so web stays up unless explicitly enabled
    if os.getenv("RUN_BOT", "0") == "0":
        log.info("[bot.main] RUN_BOT=0 -> skip bot supervisor (web-only mode)")
        return
    asyncio.run(supervise())
