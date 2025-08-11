import os
import asyncio
import logging
from flask import Blueprint, jsonify, current_app

import discord
from discord.ext import commands

# --- Flask Blueprint ---
discord_bot_bp = Blueprint("discord_bot", __name__)

FLASK_ENV = os.getenv("FLASK_ENV", "production").lower()
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN_LOCAL") if FLASK_ENV == "development" else os.getenv("DISCORD_BOT_TOKEN")

# --- Intents ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# --- Optional: simpan Flask app ---
_flask_app = None
def set_flask_app(app):
    global _flask_app
    _flask_app = app
    return _flask_app

# --- Import modular (relative) ---
from .background_tasks import run_background_tasks
from .event_handlers import register_event_handlers
from .events.advanced_events import register_advanced_events
from .helpers.error_handler import setup_error_handler
from .message_handlers import handle_on_message  # signature: handle_on_message(bot, message)

# --- Bot class & instance ---
class SatpamBot(commands.Bot):
    async def setup_hook(self):
        try:
            from .cogs_loader import load_all_cogs
            await load_all_cogs(self)
            print('[setup_hook] extensions:', list(self.extensions.keys()))
            print('[setup_hook] commands:', [c.qualified_name for c in self.commands])
        except Exception as e:
            print('[setup_hook] load cogs error:', e)

bot = SatpamBot(command_prefix="!", intents=intents, case_insensitive=True)

@bot.event
async def on_ready():
    logging.info(f"✅ Bot berhasil login sebagai {bot.user} (ID: {bot.user.id})")
    logging.info(f"🌐 Mode: {FLASK_ENV}")

    try:
        run_background_tasks(bot)
    except Exception as e:
        logging.exception("run_background_tasks error: %s", e)

    try:
        register_event_handlers(bot)
    except Exception as e:
        logging.exception("register_event_handlers error: %s", e)

    try:
        register_advanced_events(bot)
    except Exception as e:
        logging.exception("register_advanced_events error: %s", e)

    try:
        setup_error_handler(bot)
    except Exception as e:
        logging.exception("setup_error_handler error: %s", e)

# --- Safe on_message relay (no indentation issues) ---
@bot.listen("on_message")
async def _relay_on_message(message):
    if getattr(message.author, "bot", False):
        return
    try:
        await handle_on_message(bot, message)
    except Exception as e:
        logging.exception("on_message relay error: %s", e)

# --- HTTP routes ---


@bot.event
async def on_message(message: discord.Message):
    try:
        if getattr(message, "author", None) and getattr(message.author, "bot", False):
            return
        from .message_handlers import handle_on_message
        await handle_on_message(bot, message)
    except Exception:
        try:
            await bot.process_commands(message)
        except Exception:
            pass
@discord_bot_bp.route("/start-bot")
def start_bot():
    if not bot.is_closed():
        return "🤖 Bot sudah berjalan."

    token = BOT_TOKEN
    if not token:
        return f"❌ Token bot untuk mode {FLASK_ENV} tidak tersedia.", 500

    set_flask_app(current_app)
    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(token))
    return f"✅ Bot dimulai dalam mode {FLASK_ENV}."

@discord_bot_bp.route("/ping", methods=["GET"])
def ping():
    current_app.logger.info("💓 Ping dari UptimeRobot diterima.")
    return jsonify({"status": "alive"})

# --- Runner ---
def run_bot():
    token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN") or BOT_TOKEN
    if not token:
        print("[run_bot] ❌ Missing DISCORD_BOT_TOKEN (or DISCORD_TOKEN)")
        return
    bot.run(token)


@bot.event
async def on_error(event, *args, **kwargs):
    try:
        from .helpers.log_utils import send_error_log
        guild = None
        for a in list(args)[:3]:
            guild = getattr(a, "guild", None) or guild
        await send_error_log(guild, f"Unhandled error in {event}", RuntimeError("on_error"), {"event": event})
    except Exception:
        pass
