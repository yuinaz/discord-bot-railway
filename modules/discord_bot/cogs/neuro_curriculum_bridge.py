
try:
    from satpambot.bot.modules.discord_bot.cogs.neuro_curriculum_bridge import *  # noqa
except Exception:
    # safe no-op fallbacks
    def is_enabled(): return False
