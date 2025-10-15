import importlib, asyncio

COGS = [
    "satpambot.bot.modules.discord_bot.cogs.safe_mode_boot",
    "satpambot.bot.modules.discord_bot.cogs.cog_health",
    "satpambot.bot.modules.discord_bot.cogs.durable_outbox",
    "satpambot.bot.modules.discord_bot.cogs.session_epoch",
    "satpambot.bot.modules.discord_bot.cogs.ghost_predictor",
    "satpambot.bot.modules.discord_bot.cogs.slang_miner",
    "satpambot.bot.modules.discord_bot.cogs.personality_governor",
    "satpambot.bot.modules.discord_bot.cogs.state_backup",
    "satpambot.bot.modules.discord_bot.cogs.thread_log_rotator",
    "satpambot.bot.modules.discord_bot.cogs.auto_update_gate",
    "satpambot.bot.modules.discord_bot.cogs.fallback_minimal",
]

async def _load():
    class _Fake:
        def __init__(self):
            self._cogs = {}
        async def add_cog(self, c):
            self._cogs[c.__class__.__name__] = c
        def get_cog(self, name):
            return self._cogs.get(name)

    bot = _Fake()
    for modname in COGS:
        mod = importlib.import_module(modname)
        if hasattr(mod, "setup"):
            await mod.setup(bot)
    return bot

def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot = loop.run_until_complete(_load())
    print("[OK] micro smoke loaded:", ", ".join(sorted(bot._cogs.keys())))

if __name__ == "__main__":
    main()
