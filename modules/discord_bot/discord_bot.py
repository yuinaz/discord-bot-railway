cat > modules/discord_bot/discord_bot.py << 'EOF'
import os
import logging
import asyncio
import discord
from discord.ext import commands, tasks

from .helpers.env import (
    BOT_PREFIX, BOT_INTENTS, FLASK_ENV, BOT_TOKEN, LOG_CHANNEL_ID,
)
# GUILD_IDS mungkin belum ada di env.py kamu; fallback ke [] biar aman
try:
    from .helpers.env import GUILD_IDS
except Exception:
    GUILD_IDS = []

from .cogs_loader import load_cogs
from .background_tasks import run_background_tasks
from . import message_handlers
from .helpers.log_utils import upsert_status_embed, upsert_status_embed_in_channel

# Kurangi noise log lib (tetap tampil warning/error penting)
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)

# Intents
intents = BOT_INTENTS
intents.message_content = True  # pastikan prefix jalan

# Balanced: cache default, skip chunk startup, cache pesan sedang
bot = commands.Bot(
    command_prefix=BOT_PREFIX,
    intents=intents,
    help_command=None,
    chunk_guilds_at_startup=False,  # lebih cepat start, beban kecil
    max_messages=500,               # cache pesan sedang (default ~1000)
)

STATUS_TEXT = "✅ SatpamBot online dan siap berjaga."

# ---------- Heartbeat dengan tasks.loop (stabil saat resume) ----------
@tasks.loop(minutes=10)
async def status_heartbeat():
    try:
        ch = bot.get_channel(LOG_CHANNEL_ID) if LOG_CHANNEL_ID else None
        if isinstance(ch, discord.TextChannel):
            await upsert_status_embed_in_channel(ch, STATUS_TEXT)
        else:
            # fallback per-guild (by name)
            for g in bot.guilds:
                await upsert_status_embed(g, STATUS_TEXT)
    except Exception:
        pass

# ---------- Setup hook: mulai heartbeat & sync slash ----------
@bot.event
async def setup_hook():
    # Mulai heartbeat (auto-start, akan berhenti otomatis saat disconnect)
    if not status_heartbeat.is_running():
        status_heartbeat.start()

    # Sync slash commands: guild-scope (instan) lalu global (opsional)
    try:
        # Pastikan cog slash ter-load jika autoloader belum sempat
        try:
            await bot.load_extension("modules.discord_bot.cogs.slash_basic")
        except Exception:
            pass

        if GUILD_IDS:
            for gid in GUILD_IDS:
                try:
                    guild = discord.Object(id=gid)
                    await bot.tree.sync(guild=guild)  # instan di guild tsb
                    logging.info(f"[slash] synced to guild {gid}")
                except Exception as e:
                    logging.warning(f"[slash] guild sync {gid} failed: {e}")
        else:
            # Global sync (butuh waktu propagate)
            await bot.tree.sync()
            logging.info("[slash] global sync requested")
    except Exception as e:
        logging.warning(f"[slash] sync error: {e}")

@bot.event
async def on_ready():
    logging.info(f"✅ Bot berhasil login sebagai {bot.user} (ID: {bot.user.id})")
    logging.info(f"🌐 Mode: {FLASK_ENV}")

    # Upsert status sekali saat ready
    try:
        ch = bot.get_channel(LOG_CHANNEL_ID) if LOG_CHANNEL_ID else None
        if isinstance(ch, discord.TextChannel):
            await upsert_status_embed_in_channel(ch, STATUS_TEXT)
        for g in bot.guilds:
            await upsert_status_embed(g, STATUS_TEXT)
    except Exception as e:
        logging.warning(f"status upsert on_ready failed: {e}")

    # Presence loop (nama game)
    try:
        run_background_tasks(bot)  # presence: "Menjaga Server Dari Scam"
    except Exception as e:
        logging.error(f"Failed to start background tasks: {e}")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    # Pipeline (JANGAN panggil process_commands di tempat lain)
    try:
        await message_handlers.handle_on_message(bot, message)
    except Exception as e:
        logging.error(f"on_message pipeline error: {e}")
    # Satu-satunya pemanggil parser (anti dobel !tb)
    try:
        await bot.process_commands(message)
    except Exception as e:
        logging.error(f"process_commands error: {e}")

# Kompatibilitas untuk main.py (kalau ada Flask)
_flask_app = None
def set_flask_app(app):
    global _flask_app
    _flask_app = app

async def start_bot():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    await load_cogs(bot)  # autoload cogs: health, testban, prefix_guard, anti_invite_autoban, dll
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN/DISCORD_TOKEN is not set")
    await bot.start(BOT_TOKEN)

def run_bot():
    asyncio.run(start_bot())

if __name__ == "__main__":
    run_bot()
EOF
