import os
import discord
from discord.ext import commands
import logging
import asyncio

from .helpers.env import (
    BOT_PREFIX,
    BOT_INTENTS,
    OAUTH2_CLIENT_ID,
    OAUTH2_CLIENT_SECRET,
    FLASK_ENV,
)

from .cogs_loader import load_cogs
from .background_tasks import run_background_tasks
from . import message_handlers

from .helpers.log_utils import upsert_status_embed, upsert_status_embed_in_channel, LOG_CHANNEL_ID

intents = BOT_INTENTS
intents.message_content = True  # ensure prefix works

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, help_command=None)

STATUS_TEXT = "✅ SatpamBot online dan siap berjaga."

@bot.event
async def on_ready():
    logging.info(f"✅ Bot berhasil login sebagai {bot.user} (ID: {bot.user.id})")
    logging.info(f"🌐 Mode: {FLASK_ENV}")

    if not getattr(bot, "_startup_status_done", False):
        setattr(bot, "_startup_status_done", True)
        # Direct by channel id
        try:
            ch = bot.get_channel(LOG_CHANNEL_ID) if LOG_CHANNEL_ID else None
            if isinstance(ch, discord.TextChannel):
                await upsert_status_embed_in_channel(ch, STATUS_TEXT)
        except Exception as e:
            logging.warning(f"direct status upsert failed: {e}")
        # Fallback per guild
        try:
            for g in bot.guilds:
                await upsert_status_embed(g, STATUS_TEXT)
        except Exception as e:
            logging.warning(f"guild status upsert failed: {e}")

        # Heartbeat every 10 minutes
        async def _heartbeat():
            while True:
                try:
                    ch2 = bot.get_channel(LOG_CHANNEL_ID) if LOG_CHANNEL_ID else None
                    if isinstance(ch2, discord.TextChannel):
                        await upsert_status_embed_in_channel(ch2, STATUS_TEXT)
                    else:
                        for g in bot.guilds:
                            await upsert_status_embed(g, STATUS_TEXT)
                except Exception:
                    pass
                await asyncio.sleep(600)
        bot.loop.create_task(_heartbeat())

    try:
        run_background_tasks(bot)
    except Exception as e:
        logging.error(f"Failed to start background tasks: {e}")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    # Pipeline
    try:
        await message_handlers.handle_on_message(bot, message)
    except Exception as e:
        logging.error(f"on_message pipeline error: {e}")
    # Single parser
    try:
        await bot.process_commands(message)
    except Exception as e:
        logging.error(f"process_commands error: {e}")

# Flask compatibility (for main.py)
_flask_app = None
def set_flask_app(app):
    global _flask_app
    _flask_app = app

async def start_bot():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    await load_cogs(bot)
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set")
    await bot.start(token)

def run_bot():
    import asyncio
    asyncio.run(start_bot())

if __name__ == "__main__":
    run_bot()
