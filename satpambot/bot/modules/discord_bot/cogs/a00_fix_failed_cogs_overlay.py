import logging
from discord.ext import commands

log = logging.getLogger(__name__.split(".")[-1])

async def _safe_add(bot: commands.Bot, cog_obj):
    try:
        ret = bot.add_cog(cog_obj)
        if hasattr(ret, "__await__"):
            await ret
        return True
    except Exception as e:
        log.warning("add_cog failed for %s: %r", type(cog_obj).__name__, e)
        return False

async def _try_add(bot: commands.Bot, mod_name: str, cls_name: str) -> bool:
    try:
        mod = __import__(mod_name, fromlist=[cls_name])
        cls = getattr(mod, cls_name, None)
        if not cls:
            return False
        cog = cls(bot)
        return await _safe_add(bot, cog)
    except Exception as e:
        log.warning("import/add failed: %s.%s -> %r", mod_name, cls_name, e)
        return False

async def setup(bot: commands.Bot):
    candidates = [
        ("satpambot.bot.modules.discord_bot.cogs.learning_passive_observer", "LearningPassiveObserver"),
        ("satpambot.bot.modules.discord_bot.cogs.learning_passive_observer_persist", "LearningPassiveObserver"),
        ("satpambot.bot.modules.discord_bot.cogs.phish_log_sticky_example", "PhishLogStickyExample"),
        ("satpambot.bot.modules.discord_bot.cogs.phish_log_sticky_guard", "PhishLogStickyGuard"),
        ("satpambot.bot.modules.discord_bot.cogs.qna_dual_provider", "QnaDualProvider"),
        ("modules.discord_bot.cogs.learning_passive_observer", "LearningPassiveObserver"),
        ("modules.discord_bot.cogs.learning_passive_observer_persist", "LearningPassiveObserver"),
        ("modules.discord_bot.cogs.phish_log_sticky_example", "PhishLogStickyExample"),
        ("modules.discord_bot.cogs.phish_log_sticky_guard", "PhishLogStickyGuard"),
        ("modules.discord_bot.cogs.qna_dual_provider", "QnaDualProvider"),
    ]
    ok = 0
    for mod, cls in candidates:
        if await _try_add(bot, mod, cls):
            log.info("[failed_cogs_fix] loaded %s.%s", mod, cls)
            ok += 1
    if ok == 0:
        log.warning("[failed_cogs_fix] nothing loaded")
