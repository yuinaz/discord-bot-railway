#!/usr/bin/env python3
import os, sys, types, asyncio

def info(msg): print(msg, flush=True)

def _make_dummy_bot():
    Guild = type("Guild", (), {})
    g = Guild(); g.id = 999999
    Bot = type("Bot", (), {})
    b = Bot(); b.guilds = [g]
    return b

async def main():
    info("======== USING REPO (PYTHONPATH=.) ========")
    try:
        import importlib
        a26 = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.a26_memory_upsert_thread_router")
    except Exception as e:
        info(f"FAIL: could not import a26 wrapper: {e!r}")
        sys.exit(1)

    # Monkey patch _original menjadi dummy async function agar offline
    calls = []
    async def _dummy_original(bot, guild_id, channel_id, title, **kw):
        calls.append(dict(guild_id=guild_id, channel_id=channel_id, title=title, extra=kw))
        return True

    # Ganti target original
    a26._original = _dummy_original

    # Set ENV agar bisa derive kalau payload tidak isi gid/chid
    os.environ.setdefault("GUILD_METRICS_ID", "123")
    os.environ.setdefault("PUBLIC_REPORT_CHANNEL_ID", "456")
    os.environ.setdefault("MEMORY_UPSERT_TITLE", "XP: Miner Memory")

    bot = _make_dummy_bot()

    # Case 1: dict payload (harus sukses & TIDAK **payload)
    payload = {"phish_text": "abc", "ts": 1712345678}
    ok1 = await a26._patched_memroute(bot, payload)
    if not ok1:
        info("FAIL: dict payload path returned False")
        sys.exit(1)

    # Verifikasi panggilan pertama
    if not calls or calls[0]["guild_id"] != 123 or calls[0]["channel_id"] != 456:
        info(f"FAIL: wrong args on dict path: {calls[0] if calls else None}")
        sys.exit(1)
    # Pastikan 'payload' dikirim sebagai 'payload=' bukan kwargs unpack
    if "payload" not in calls[0]["extra"] or calls[0]["extra"]["payload"] != payload:
        info("FAIL: payload tidak dikirim sebagai keyword 'payload='")
        sys.exit(1)

    # Case 2: legacy positional passthrough
    ok2 = await a26._patched_memroute(bot, 1, 2, "T")
    if not ok2:
        info("FAIL: legacy positional path returned False")
        sys.exit(1)

    info("OK: repo path memroute wrapper logic (dict payload + positional)")
    info("RESULT: OK")

if __name__ == "__main__":
    # Pastikan bisa run dari repo root: PYTHONPATH=. python scripts/smoke_memroute_offline.py --use-repo
    asyncio.run(main())
