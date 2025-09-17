# satpambot/bot/modules/discord_bot/cogs/cogs_loader.py
from __future__ import annotations
import logging
from discord.ext import commands
log = logging.getLogger(__name__)
EXTENSIONS = (
    "satpambot.bot.modules.discord_bot.cogs.prefix_mod_only",
    "satpambot.bot.modules.discord_bot.cogs.error_notifier",
    "satpambot.bot.modules.discord_bot.cogs.reaction_allowlist_static",
    "satpambot.bot.modules.discord_bot.cogs.status_pin_updater",
    "satpambot.bot.modules.discord_bot.cogs.ban_local_notify",
)
async def _safe_load(bot: commands.Bot, name: str) -> None:
    try:
        loaded = getattr(bot, "extensions", {})
        if isinstance(loaded, dict) and name in loaded:
            log.info("[cogs_loader] already loaded: %s", name); return
    except Exception: pass
    try:
        await bot.load_extension(name); log.info("[cogs_loader] loaded: %s", name)
    except Exception as e:
        log.warning("[cogs_loader] failed to load %s: %r", name, e)
async def setup(bot: commands.Bot) -> None:
    for ext in EXTENSIONS:
        await _safe_load(bot, ext)
