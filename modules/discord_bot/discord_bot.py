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

def _resolve_log_channel() -> discord.TextChannel | None:
    """Ambil channel dari LOG_CHANNEL_ID + LOG ke console supaya gampang cek di Render."""
    ch = bot.get_channel(LOG_CHANNEL_ID) if LOG_CHANNEL_ID else None
    if isinstance(ch, discord.TextChannel):
        logging.info(
            f"[status] using LOG_CHANNEL_ID={LOG_CHANNEL_ID} "
            f"resolved_to=#{ch.name} (id={ch.id}) in guild='{ch.guild.name}' (id={ch.guild.id})"
        )
        return ch
    # Saat warm-up (belum ready), jangan bikin warning supaya log bersih
    if bot.is_ready():
        logging.warning(
            f"[status] LOG_CHANNEL_ID={LOG_CHANNEL_ID} not found/visible. "
            f"Pastikan bot punya izin melihat & menulis di channel itu."
        )
    else:
        logging.info("[status] warm-up: channel belum tersedia (bot belum ready)")
    return None

# ---------- Heartbeat 10 menit (HANYA ke LOG_CHANNEL_ID) ----------
@tasks.loop(minutes=10)
async def status_heartbeat():
    ch = _resolve_log_channel()
    if ch:
        await upsert_status_embed_in_channel(ch, STATUS_TEXT)

# Pastikan loop baru jalan setelah bot benar-benar ready
@status_heartbeat.before_loop
async def _hb_before_loop():
    await bot.wait_until_ready()
    await asyncio.sleep(2)  # beri jeda kecil agar cache channel terisi

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
    logging.info(f"[status] ENV LOG_CHANNEL_ID={LOG_CHANNEL_ID}")

    # Upsert status sekali saat ready (HANYA ke LOG_CHANNEL_ID)
    ch = _resolve_log_channel()
    if ch:
        try:
            await upsert_status_embed_in_channel(ch, STATUS_TEXT)
        except Exception as e:
            logging.warning(f"[status] upsert failed: {e}")

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

# Hook pesan untuk parser dari log channel ban
@bot.event
async def on_message(message):
    try:
        from .event_handlers import on_message_parser
        if callable(on_message_parser):
            await on_message_parser(message)
    except Exception as e:
        print("[discord_bot] on_message parser error", e)
    await bot.process_commands(message)
