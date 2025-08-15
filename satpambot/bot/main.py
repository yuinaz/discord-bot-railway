# -*- coding: utf-8 -*-
"""
Resilient Discord bot bootstrapper (permanent + legacy shim)
- Prioritizes: satpambot.bot.modules.discord_bot.discord_bot
- Installs a 'modules' shim at runtime for legacy absolute imports
- Supports async/sync entrypoints (main/run_bot/run/start)
- Optional supervisor (auto-restart) via BOT_SUPERVISE=1 (default 1)
"""

import os, sys, asyncio, importlib, inspect, traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SATPAMBOT_DIR = os.path.dirname(BASE_DIR)          # .../satpambot
REPO_ROOT = os.path.dirname(SATPAMBOT_DIR)         # repo root

# Ensure search paths
for p in (REPO_ROOT, SATPAMBOT_DIR):
    if p and p not in sys.path:
        sys.path.insert(0, p)

# ---- Install legacy 'modules' alias so imports like 'modules.discord_bot.*' work ----
try:
    if 'modules' not in sys.modules:
        sys.modules['modules'] = importlib.import_module('satpambot.bot.modules')
except Exception as _e:
    # Non-fatal; bootstrap will still try monorepo paths
    print('[WARN] legacy modules shim unavailable:', _e)

def _env(k, default=None):
    v = os.getenv(k)
    return v if v not in (None, "") else default

def candidates():
    # Permanent correct path for your repo
    yield "satpambot.bot.modules.discord_bot.discord_bot"
    # Other guesses (legacy/alternative)
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
