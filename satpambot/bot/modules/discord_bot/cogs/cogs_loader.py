from __future__ import annotations

import logging, sys
from discord.ext import commands

log = logging.getLogger(__name__)

EXTENSIONS = (

                    "satpambot.bot.modules.discord_bot.cogs.runtime_cfg_manager",
    "satpambot.bot.modules.discord_bot.cogs.runtime_cfg_from_message",
    "satpambot.bot.modules.discord_bot.cogs.prefix_mod_only",
    "satpambot.bot.modules.discord_bot.cogs.error_notifier",
    "satpambot.bot.modules.discord_bot.cogs.reaction_allowlist_static",
    "satpambot.bot.modules.discord_bot.cogs.status_pin_updater",
    "satpambot.bot.modules.discord_bot.cogs.ban_local_notify",
    "satpambot.bot.modules.discord_bot.cogs.public_send_router",
    "satpambot.bot.modules.discord_bot.cogs.phish_reward_listener",
    "satpambot.bot.modules.discord_bot.cogs.a01_xp_checkpoint_discord_backend",
    "satpambot.bot.modules.discord_bot.cogs.a08_public_clearchat",
    "satpambot.bot.modules.discord_bot.cogs.public_chat_gate",
    "satpambot.bot.modules.discord_bot.cogs.repo_guild_sync_bootstrap",
    "satpambot.bot.modules.discord_bot.cogs.a02_miner_accel_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a06_sticky_status_strict_overlay",
    "satpambot.bot.modules.discord_bot.cogs.vision_captioner",
    "satpambot.bot.modules.discord_bot.cogs.qna_dual_provider",
    "satpambot.bot.modules.discord_bot.cogs.admin_sync",
    "satpambot.bot.modules.discord_bot.cogs.admin_repo_control",
    "satpambot.bot.modules.discord_bot.cogs.github_repo_sync",
    "satpambot.bot.modules.discord_bot.cogs.repo_pull_and_restart",
    "satpambot.bot.modules.discord_bot.cogs.weekly_xp_guard",
    "satpambot.bot.modules.discord_bot.cogs.force_sync_autoheal",
)

async def _safe_load(bot: commands.Bot, name: str) -> None:
    try:
        loaded = getattr(bot, "extensions", {})
        if isinstance(loaded, dict) and name in loaded:
            log.info("[cogs_loader] already loaded: %s", name); return
    except Exception:
        pass
    if name in sys.modules:
        log.info("[cogs_loader] already in sys.modules: %s", name); return
    try:
        await bot.load_extension(name)
        log.info("[cogs_loader] loaded: %s", name)
    except Exception as e:
        msg = f"{e}"
        if "already loaded" in msg:
            log.info("[cogs_loader] already loaded (caught): %s", name)
        else:
            log.warning("[cogs_loader] failed to load %s: %r", name, e)

async def setup(bot: commands.Bot) -> None:
    for ext in EXTENSIONS:
        await _safe_load(bot, ext)
    try:
        log.info("[cogs_loader] summary loaded: %s", sorted(getattr(bot, "extensions", {}).keys()))
    except Exception:
        pass
