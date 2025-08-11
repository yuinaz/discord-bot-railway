# modules/discord_bot/discord_bot.py
from __future__ import annotations

import asyncio
import logging
import discord
from discord.ext import commands

# ===== Try to import project helpers, but don't crash editor/runtime if unavailable =====
try:
    from .helpers.env import (
        BOT_PREFIX,
        BOT_INTENTS,
        OAUTH2_CLIENT_ID,
        OAUTH2_CLIENT_SECRET,
        FLASK_ENV,
        get_bot_token,
        get_profile,
    )
except Exception:
    # Reasonable fallbacks for local editing/testing
    BOT_PREFIX = "!"
    intents = discord.Intents.default()
    intents.message_content = True
    BOT_INTENTS = intents
    OAUTH2_CLIENT_ID = None
    OAUTH2_CLIENT_SECRET = None
    FLASK_ENV = "production"
    def get_bot_token():
        import os
        return os.getenv("BOT_TOKEN") or os.getenv("DISCORD_BOT_TOKEN") or ""
    def get_profile():
        return "default"

try:
    from .cogs_loader import load_cogs
except Exception:
    async def load_cogs(_bot):  # fallback: no cogs
        logging.warning("load_cogs fallback used: cogs_loader not available")

try:
    from .background_tasks import run_background_tasks
except Exception:
    def run_background_tasks(_bot):
        logging.info("run_background_tasks fallback used")

try:
    from . import message_handlers
except Exception:
    class _MH:
        async def handle_on_message(bot, message):
            return
    message_handlers = _MH()

# Optional log helpers (don't crash if missing)
try:
    from .helpers.log_utils import upsert_status_embed, upsert_status_embed_in_channel, LOG_CHANNEL_ID
except Exception:
    async def upsert_status_embed(*args, **kwargs): pass
    async def upsert_status_embed_in_channel(*args, **kwargs): pass
    LOG_CHANNEL_ID = None

# ===== Bot & intents =====
intents = BOT_INTENTS
intents.message_content = True  # ensure message content intent enabled

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, help_command=None)
STATUS_TEXT = "✅ SatpamBot online dan siap berjaga."

# Optional Flask app holder for compatibility with main.py that might call set_flask_app()
_flask_app = None
def set_flask_app(app):
    """Store a reference to a Flask app (optional, backward compatible)."""
    global _flask_app
    _flask_app = app
    logging.info("Flask app registered into discord_bot module")

# ===== Events =====
@bot.event
async def on_ready():
    logging.info(f"✅ Bot berhasil login sebagai {bot.user} (ID: {bot.user.id})")
    try:
        profile = get_profile()
    except Exception:
        profile = "default"
    logging.info(f"🌐 Mode: {profile} ({FLASK_ENV})")

    if not getattr(bot, "_startup_status_done", False):
        setattr(bot, "_startup_status_done", True)

        # Presence sederhana
        try:
            await bot.change_presence(activity=discord.Game(name="Satpam aktif"), status=discord.Status.online)
        except Exception as e:
            logging.warning(f"change_presence failed: {e}")

        # Upsert status/embed (anti-spam: helper akan edit pesan lama)
        try:
            ch = bot.get_channel(LOG_CHANNEL_ID) if LOG_CHANNEL_ID else None
            if isinstance(ch, discord.TextChannel):
                await upsert_status_embed_in_channel(ch, STATUS_TEXT, force=False)
            else:
                for g in list(bot.guilds):
                    try:
                        await upsert_status_embed(g, STATUS_TEXT, force=False)
                    except Exception:
                        pass
        except Exception as e:
            logging.warning(f"status upsert failed: {e}")

        # Heartbeat 10 menit sekali (edit, bukan kirim baru)
        async def _heartbeat():
            await bot.wait_until_ready()
            while not bot.is_closed():
                try:
                    ch2 = bot.get_channel(LOG_CHANNEL_ID) if LOG_CHANNEL_ID else None
                    if isinstance(ch2, discord.TextChannel):
                        await upsert_status_embed_in_channel(ch2, STATUS_TEXT, force=False)
                    else:
                        for g in list(bot.guilds):
                            try:
                                await upsert_status_embed(g, STATUS_TEXT, force=False)
                            except Exception:
                                pass
                except Exception as e:
                    logging.warning(f"[heartbeat] {e}")
                await asyncio.sleep(600)

        try:
            bot.loop.create_task(_heartbeat())
        except Exception as e:
            logging.warning(f"failed to schedule heartbeat: {e}")

    # Start background tasks (punyamu)
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
        await bot.process_commands(message)
    except Exception as e:
        logging.error(f"process_commands error: {e}")

# ===== Entrypoints =====
async def start_bot():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    await load_cogs(bot)
    token = get_bot_token()
    if not token:
        raise RuntimeError("BOT_TOKEN is not set (cek DISCORD_BOT_TOKEN_LOCAL / DISCORD_BOT_TOKEN / BOT_TOKEN)")
    await bot.start(token)

def run_bot():
    asyncio.run(start_bot())

if __name__ == "__main__":
    run_bot()
