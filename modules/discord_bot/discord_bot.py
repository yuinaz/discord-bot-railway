import os
import logging
import asyncio
import discord
from discord.ext import commands, tasks

from .helpers.env import BOT_PREFIX, BOT_INTENTS, FLASK_ENV, BOT_TOKEN, LOG_CHANNEL_ID
from .cogs_loader import load_cogs
from .background_tasks import run_background_tasks
from . import message_handlers
from .helpers.log_utils import upsert_status_embed_in_channel

# Kurangi noise log lib
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)

# Intents
intents = BOT_INTENTS
intents.message_content = True  # pastikan prefix jalan

# Balanced: startup cepat & cache sedang
bot = commands.Bot(
    command_prefix=BOT_PREFIX,
    intents=intents,
    help_command=None,
    chunk_guilds_at_startup=False,
    max_messages=500,
)

STATUS_TEXT = "✅ SatpamBot online dan siap berjaga."

# ---------- Heartbeat 10 menit (HANYA ke LOG_CHANNEL_ID) ----------
@tasks.loop(minutes=10)
async def status_heartbeat():
    ch = bot.get_channel(LOG_CHANNEL_ID) if LOG_CHANNEL_ID else None
    if isinstance(ch, discord.TextChannel):
        await upsert_status_embed_in_channel(ch, STATUS_TEXT)
    else:
        logging.warning("Heartbeat skipped: LOG_CHANNEL_ID not found/visible.")

@bot.event
async def setup_hook():
    if not status_heartbeat.is_running():
        status_heartbeat.start()
    # (opsional) autoload slash_basic kalau ada
    try:
        await bot.load_extension("modules.discord_bot.cogs.slash_basic")
    except Exception:
        pass

@bot.event
async def on_ready():
    logging.info(f"✅ Bot berhasil login sebagai {bot.user} (ID: {bot.user.id})")
    logging.info(f"🌐 Mode: {FLASK_ENV}")

    # Upsert status sekali saat ready (HANYA ke LOG_CHANNEL_ID)
    ch = bot.get_channel(LOG_CHANNEL_ID) if LOG_CHANNEL_ID else None
    if isinstance(ch, discord.TextChannel):
        try:
            await upsert_status_embed_in_channel(ch, STATUS_TEXT)
        except Exception as e:
            logging.warning(f"status upsert failed: {e}")
    else:
        logging.warning("on_ready: LOG_CHANNEL_ID not found/visible; status skipped.")

    # Presence loop (“Menjaga Server Dari Scam”)
    try:
        run_background_tasks(bot)
    except Exception as e:
        logging.error(f"Failed to start background tasks: {e}")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    # Pipeline (tanpa panggil parser di tempat lain)
    try:
        await message_handlers.handle_on_message(bot, message)
    except Exception as e:
        logging.error(f"on_message pipeline error: {e}")
    # Satu-satunya parser call
    try:
        await bot.process_commands(message)
    except Exception as e:
        logging.error(f"process_commands error: {e}")

# Kompatibilitas main.py (kalau ada Flask)
_flask_app = None
def set_flask_app(app):
    global _flask_app
    _flask_app = app

async def start_bot():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    await load_cogs(bot)
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN/DISCORD_TOKEN is not set")
    await bot.start(BOT_TOKEN)

def run_bot():
    asyncio.run(start_bot())

if __name__ == "__main__":
    run_bot()
