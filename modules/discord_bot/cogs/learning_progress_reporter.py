
try:
    from satpambot.bot.modules.discord_bot.cogs.learning_progress_reporter import *  # noqa
except Exception:
    async def report(*args, **kwargs): return False
