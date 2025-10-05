# satpambot/bot/modules/discord_bot/shim_runner.py







import logging
import os

import discord
from discord.ext import commands

try:







    from .cogs_loader import load_cogs







except Exception:







    from satpambot.bot.modules.discord_bot.cogs_loader import load_cogs  # type: ignore















log = logging.getLogger(__name__)















# ===== Intents =====







intents = discord.Intents.default()







intents.guilds = True







intents.members = True  # required for some moderation checks & metrics online count







intents.presences = True  # metrics online count







intents.message_content = True  # ensure enabled in Discord Dev Portal















PREFIX = os.getenv("COMMAND_PREFIX", "!")







allowed_mentions = discord.AllowedMentions(everyone=False, users=True, roles=False, replied_user=False)















bot = commands.Bot(command_prefix=PREFIX, intents=intents, allowed_mentions=allowed_mentions)























# ===== Events =====







@bot.event







async def on_ready():







    try:







        from satpambot.bot.modules.discord_bot.helpers import log_utils







    except Exception:







        log_utils = None  # type: ignore















    import time















    if not getattr(bot, "start_time", None):







        bot.start_time = time.time()







    try:







        if log_utils:







            for g in list(getattr(bot, "guilds", []) or []):







                log_utils.log_startup_status(bot, g)







    except Exception:







        pass







    try:







        log.info("✅ Bot login as %s (%s)", bot.user, bot.user.id if bot.user else "?")







    except Exception:







        log.info("✅ Bot login.")























@bot.event







async def setup_hook():







    # muat semua cogs default via loader







    try:







        await load_cogs(bot)







    except Exception as e:







        log.error("Failed to load cogs: %s", e, exc_info=True)















    # === Tambahan: pastikan live_metrics_push ter-load ===







    # Bisa dimatikan dengan METRICS_DISABLE=1







    if os.getenv("METRICS_DISABLE", "0") not in ("1", "true", "TRUE"):







        ext = "satpambot.bot.modules.discord_bot.cogs.live_metrics_push"







        try:







            # Discord.py 2.x mendukung setup async/sync; cog sudah menyediakan keduanya.







            if ext not in bot.extensions:







                await bot.load_extension(ext)







                log.info("✅ Loaded metrics cog: %s", ext)







            else:







                log.info("ℹ️ Metrics cog already loaded: %s", ext)







        except Exception as e:







            log.error("⚠️ Could not load metrics cog (%s): %s", ext, e, exc_info=True)























# ===== Entrypoint =====







async def start_bot():







    token = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")







    if not token:







        raise RuntimeError("ENV DISCORD_TOKEN / BOT_TOKEN tidak diset")







    await bot.start(token)























# ===== Bridge bot -> dashboard (opsional) =====







try:







    from satpambot.dashboard.discord_bridge import set_bot as _dash_set_bot















    _dash_set_bot(bot)







except Exception:







    pass







