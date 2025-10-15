import asyncio, importlib, sys, traceback
from satpambot.testing.fake_discord import FakeBot

COGS = [
    "satpambot.bot.modules.discord_bot.cogs.chat_neurolite",
    "satpambot.bot.modules.discord_bot.cogs.sticker_feedback",
    "satpambot.bot.modules.discord_bot.cogs.sticker_text_feedback",
    "satpambot.bot.modules.discord_bot.cogs.memory_tuner",
    "satpambot.bot.modules.discord_bot.cogs.owner_notify_conv",
    "satpambot.bot.modules.discord_bot.cogs.self_check_boot",
]

async def _load():
    bot = FakeBot()
    for modname in COGS:
        mod = importlib.import_module(modname)
        setup = getattr(mod, "setup")
        await setup(bot)
    # emit on_ready listeners if any (they are registered via decorators, will be invoked by Discord normally)
    # Our fake emitter can't auto-discover listeners, so we just ensure setup didn't crash.
    return bot

def main():
    loop = asyncio.get_event_loop()
    bot = loop.run_until_complete(_load())
    print("[OK] cogs loaded into FakeBot:", ", ".join(bot.cogs.keys()))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        traceback.print_exc()
        sys.exit(2)
