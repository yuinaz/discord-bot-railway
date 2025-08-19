import os, logging, discord
from discord.ext import commands
try:
    from .cogs_loader import load_cogs
except Exception:
    from satpambot.bot.modules.discord_bot.cogs_loader import load_cogs  # type: ignore

log = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.guilds = True
intents.members = True  # required for some moderation checks
intents.message_content = True  # ensure enabled in Discord Dev Portal

PREFIX = os.getenv("COMMAND_PREFIX", "!")
allowed_mentions = discord.AllowedMentions(everyone=False, users=True, roles=False, replied_user=False)

bot = commands.Bot(command_prefix=PREFIX, intents=intents, allowed_mentions=allowed_mentions)

@bot.event
async def on_ready():
    import time
    try:
        from satpambot.bot.modules.discord_bot.helpers import log_utils
    except Exception:
        log_utils=None  # type: ignore
    
    import time
    if not getattr(bot, 'start_time', None): bot.start_time = time.time()
    try:
        if log_utils:
            for g in list(getattr(bot, 'guilds', []) or []):
                log_utils.log_startup_status(bot, g)
    except Exception:
        pass
    try:
        log.info("✅ Bot login as %s (%s)", bot.user, bot.user.id if bot.user else "?")
    except Exception:
        log.info("✅ Bot login.")

@bot.event
async def setup_hook():
    try:
        await load_cogs(bot)
    except Exception as e:
        log.error("Failed to load cogs: %s", e, exc_info=True)

async def start_bot():
    token = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("ENV DISCORD_TOKEN / BOT_TOKEN tidak diset")
    await bot.start(token)
