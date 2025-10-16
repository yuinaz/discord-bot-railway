
# import-compat alias: expose satpambot cogs under modules.discord_bot.cogs
try:
    from satpambot.bot.modules.discord_bot.cogs import *  # noqa
except Exception:
    pass
