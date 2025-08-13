from __future__ import annotations
import os
import logging
import asyncio
import discord
from discord.ext import commands, tasks

from .helpers.env import BOT_PREFIX, BOT_INTENTS, FLASK_ENV, BOT_TOKEN
try:
    from modules.discord_bot.helpers.status_logger_patch import announce_status
except Exception:
    async def announce_status(*args, **kwargs):
        return None
try:
    from modules.discord_bot.helpers.status_logger_patch import log_selected_channel
except Exception:
    def log_selected_channel(*args, **kwargs):
        pass
try:
    from modules.discord_bot.helpers.log_once import log_once
except Exception:
    def log_once(key, printer):
        try:
            printer()
        except Exception:
            pass
from modules.discord_bot.helpers import env
from .cogs_loader import load_cogs
from .background_tasks import run_background_tasks
from . import message_handlers
from .helpers.log_utils import upsert_status_embed_in_channel
from modules.discord_bot.helpers.status_logger_patch import log_env_summary_once

# Kurangi noise log lib
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)

# ===== Intents & bot config (startup ringan untuk 1 server) =====
# Gunakan intents minimum yang dibutuhkan saja
intents = discord.Intents.none()
intents.guilds = True
intents.messages = True
intents.message_content = True  # butuh utk prefix/handler

member_cache_flags = discord.MemberCacheFlags.none()  # no member cache

bot = commands.Bot(
    command_prefix=BOT_PREFIX,
    intents=intents,
    help_command=None,
    chunk_guilds_at_startup=False,        # jangan chunk member saat start
    member_cache_flags=member_cache_flags,
    max_messages=300,                     # buffer lebih kecil
)

STATUS_TEXT = "✅ SatpamBot online dan siap berjaga."
_RESOLVED_LOG_CHANNEL_ID = None

def _resolve_log_channel() -> discord.TextChannel | None:
    """Resolve log channel sekali, cache ID supaya tidak spam log."""
    global _RESOLVED_LOG_CHANNEL_ID
    if _RESOLVED_LOG_CHANNEL_ID:
        ch = bot.get_channel(_RESOLVED_LOG_CHANNEL_ID)
        if isinstance(ch, discord.TextChannel):
            return ch

    # Try by ID
    try:
        log_id = getattr(env, "LOG_CHANNEL_ID", 0) or 0
        if log_id:
            ch = bot.get_channel(log_id)
            if isinstance(ch, discord.TextChannel):
                try:
                    log_selected_channel(ch, by="id")
                finally:
                    _RESOLVED_LOG_CHANNEL_ID = ch.id
                return ch
    except Exception as e:
        logging.debug("[status] id lookup error: %s", e)

    # Fallback by NAME
    try:
        name = getattr(env, "LOG_CHANNEL_NAME", "").lstrip("#").strip()
        if name:
            for g in bot.guilds:
                for ch in getattr(g, "text_channels", []):
                    if getattr(ch, "name", None) == name:
                        try:
                            log_selected_channel(ch, by="name")
                        finally:
                            _RESOLVED_LOG_CHANNEL_ID = ch.id
                        return ch
    except Exception as e:
        logging.debug("[status] name lookup error: %s", e)

    if bot.is_ready():
        log_once("no_log_channel_found", lambda: logging.warning("[status] no log channel found via ID or NAME. Pastikan izin & nama channel benar."))
    else:
        logging.info("[status] warm-up: channel belum tersedia (bot belum ready)")
    return None

# ---------- Heartbeat 10 menit (HANYA ke LOG_CHANNEL_ID) ----------
@tasks.loop(minutes=10)
async def status_heartbeat():
    ch = _resolve_log_channel()
    if ch:
        await upsert_status_embed_in_channel(ch, STATUS_TEXT)

@status_heartbeat.before_loop
async def _hb_before_loop():
    await bot.wait_until_ready()
    await asyncio.sleep(2)

@bot.event
async def setup_hook():
    if not status_heartbeat.is_running():
        status_heartbeat.start()
    try:
        await bot.load_extension("modules.discord_bot.cogs.slash_basic")
    except Exception:
        pass

@bot.event
async def on_ready():
    try:
        for g in bot.guilds:
            await announce_status(g, bot)
    except Exception as e:
        logging.warning("[status] announce_status error: %s", e)

    logging.info(f"✅ Bot berhasil login sebagai {bot.user} (ID: {bot.user.id})")
    logging.info(f"🌐 Mode: {FLASK_ENV}")
    log_env_summary_once()

    ch = _resolve_log_channel()
    if ch:
        try:
            await upsert_status_embed_in_channel(ch, STATUS_TEXT)
        except Exception as e:
            logging.warning(f"[status] upsert failed: {e}")

    try:
        run_background_tasks(bot)
    except Exception as e:
        logging.error(f"Failed to start background tasks: {e}")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    try:
        await message_handlers.handle_on_message(bot, message)
    except Exception as e:
        logging.error(f"on_message pipeline error: {e}")
    try:
        from .event_handlers import on_message_parser
        if callable(on_message_parser):
            await on_message_parser(message)
    except Exception as e:
        logging.error(f"event_handlers.on_message_parser error: {e}")
    try:
        await bot.process_commands(message)
    except Exception as e:
        logging.error(f"process_commands error: {e}")

_socketio = None
def set_socketio(sio):
    global _socketio
    _socketio = sio

_flask_app = None
def set_flask_app(app):
    global _flask_app
    _flask_app = app

async def start_bot():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    await load_cogs(bot)
    from .helpers.env import BOT_TOKEN as BOT_TOKEN_CONF
    token = (
        os.getenv('BOT_TOKEN')
        or os.getenv('DISCORD_TOKEN')
        or os.getenv('DISCORD_BOT_TOKEN')
        or os.getenv('DISCORD_BOT_TOKEN_LOCAL')
        or BOT_TOKEN_CONF
    )
    if not token:
        raise RuntimeError('BOT_TOKEN/DISCORD_TOKEN is not set')
    await bot.start(token)

def run_bot():
    asyncio.run(start_bot())

if __name__ == "__main__":
    run_bot()
