import os, logging, discord
from discord.ext import commands
try:
    from .cogs_loader import load_cogs
except Exception:
    from satpambot.bot.modules.discord_bot.cogs_loader import load_cogs  # type: ignore

log = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    log.info("✅ Bot login as %s (%s)", bot.user, bot.user.id if bot.user else "?")

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
