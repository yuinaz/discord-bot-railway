#!/usr/bin/env python3
# Optional runtime monkeypatch (tidak mengubah file). Jalankan sebelum smoke_deep jika perlu.
import sys, os, types, asyncio

sys.path.append(os.getcwd())

try:
    import satpambot.bot.modules.discord_bot.helpers.smoke_utils as su
except Exception as e:
    print("[err] import failed:", e)
    raise

def ensure_async_waitready(cls):
    if hasattr(cls, "wait_until_ready") and asyncio.iscoroutinefunction(getattr(cls, "wait_until_ready")):
        return False
    async def wait_until_ready(self):
        return
    setattr(cls, "wait_until_ready", wait_until_ready)
    return True

patched = []

if hasattr(su, "DummyBot"):
    if ensure_async_waitready(su.DummyBot):
        patched.append("DummyBot")
if hasattr(su, "_DummyBot"):
    if ensure_async_waitready(su._DummyBot):
        patched.append("_DummyBot")
elif hasattr(su, "DummyBot"):
    su._DummyBot = su.DummyBot
    ensure_async_waitready(su._DummyBot)
    patched.append("_DummyBot(alias)")

print("[monkey] patched:", ", ".join(patched) if patched else "(none)")
