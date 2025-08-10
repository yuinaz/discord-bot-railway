import os
import asyncio
import logging

from flask import Blueprint, request, jsonify, current_app

import discord
from discord.ext import commands

# ---- Flask Blueprint ----
discord_bot_bp = Blueprint("discord_bot", __name__)

# ---- Mode & token selection ----
FLASK_ENV = os.getenv("FLASK_ENV", "production").lower()
if FLASK_ENV == "development":
    BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN_LOCAL")
else:
    BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# ---- Intents ----
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

# ---- Optional: Flask app handle for cross-module access ----
_flask_app = None
def set_flask_app(app):
    global _flask_app
    _flask_app = app
    return _flask_app

# ---- Modular Imports (lazy where possible) ----
from modules.discord_bot.background_tasks import run_background_tasks
from modules.discord_bot.event_handlers import register_event_handlers
from modules.discord_bot.events.advanced_events import register_advanced_events
from modules.discord_bot.helpers.error_handler import setup_error_handler
from modules.discord_bot.message_handlers import handle_on_message

# ---- Bot class with setup_hook to load cogs early ----
class SatpamBot(commands.Bot):
    async def setup_hook(self):
        try:
            from modules.discord_bot.cogs_loader import load_all_cogs
            await load_all_cogs(self)
            print('[setup_hook] extensions:', list(self.extensions.keys()))
            print('[setup_hook] commands:', [c.qualified_name for c in self.commands])
        except Exception as e:
            print('[setup_hook] load cogs error:', e)

# ---- Create bot instance BEFORE using @bot.event ----
bot = SatpamBot(command_prefix="!", intents=intents, case_insensitive=True)

# ---- Event handlers ----
@bot.event
async def on_ready():
    logging.info(f"✅ Bot berhasil login sebagai {bot.user} (ID: {bot.user.id})")
    logging.info(f"🌐 Mode: {FLASK_ENV}")

    # Start background tasks & register handlers
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

    # Error handler & message listener
    try:
        setup_error_handler(bot)
    except Exception as e:
        logging.exception("setup_error_handler error: %s", e)

    try:
        bot.add_listener(handle_on_message, "on_message")
    except Exception as e:
        logging.exception("add_listener on_message error: %s", e)

# ---- HTTP endpoints to control bot (optional) ----
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

# ---- Runner for thread/process usage ----
def run_bot():
    token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN") or BOT_TOKEN
    if not token:
        print("[run_bot] ❌ Missing DISCORD_BOT_TOKEN (or DISCORD_TOKEN)")
        return
    bot.run(token)
