# -*- coding: utf-8 -*-
"""
Resilient Discord bot bootstrapper (permanent path)
- Prioritizes: satpambot.bot.modules.discord_bot.discord_bot  (your repo's actual path)
- Supports async/sync entrypoints (main/run_bot/run/start)
- Optional supervisor (auto-restart) via BOT_SUPERVISE=1 (default 1)
- Still allows overrides via BOT_ENTRY / BOT_FUNC if you ever need them, but NOT required.
"""

import os, sys, asyncio, importlib, inspect, traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SATPAMBOT_DIR = os.path.dirname(BASE_DIR)          # .../satpambot
REPO_ROOT = os.path.dirname(SATPAMBOT_DIR)         # repo root

# Ensure repo root and /satpambot are importable
for p in (REPO_ROOT, SATPAMBOT_DIR):
    if p and p not in sys.path:
        sys.path.insert(0, p)

def _env(k, default=None):
    v = os.getenv(k)
    return v if v not in (None, "") else default

def candidates():
    # 1) Permanent correct path for your repo (no env needed)
    yield "satpambot.bot.modules.discord_bot.discord_bot"
    # 2) Optional explicit override via env (if ever needed)
    e = _env("BOT_ENTRY")
    if e:
        yield e
    # 3) Other guesses (legacy/alternative layouts)
    for name in (
        "modules.discord_bot.discord_bot",
        "satpambot.modules.discord_bot.discord_bot",
        "satpambot.bot.discord_bot",
        "satpambot.bot.discord_bot.main",
        "discord_bot.discord_bot",
    ):
        yield name

def find_entry(mod):
    fn = _env("BOT_FUNC")
    if fn and hasattr(mod, fn):
        return getattr(mod, fn)
    for name in ("main", "run_bot", "run", "start"):
        if hasattr(mod, name):
            return getattr(mod, name)
    return None

async def run_once():
    token = _env("DISCORD_TOKEN") or _env("BOT_TOKEN")
    if not token:
        raise RuntimeError("ENV DISCORD_TOKEN / BOT_TOKEN tidak diset")
    last = None
    tried = []
    for name in candidates():
        try:
            mod = importlib.import_module(name)
            entry = find_entry(mod)
            if not entry:
                tried.append(f"{name} (no entry)")
                continue
            res = entry()
            if inspect.iscoroutine(res):
                await res
            elif inspect.iscoroutinefunction(entry):
                await entry()  # type: ignore
            return
        except Exception as e:
            last = e
            tried.append(f"{name} ({e})")
    raise ImportError("Tidak menemukan modul bot. Tried: " + ", ".join(tried)) from last

async def supervise():
    if _env("BOT_SUPERVISE", "1") == "0":
        return await run_once()
    delay = int(_env("BOT_RETRY_DELAY", "12") or "12")
    while True:
        try:
            await run_once()
            return
        except Exception as e:
            print("[ERROR] Bot crash:", e)
            traceback.print_exc()
            print(f"[INFO] restart in {delay}s...")
            await asyncio.sleep(delay)

def main():
    try:
        asyncio.run(supervise())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
