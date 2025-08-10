import os
from modules.discord_bot.helpers.env_loader import load_env
import asyncio
import logging
import os
from modules.discord_bot.helpers.env_loader import load_env
from flask import Blueprint, request, jsonify, current_app
import discord
from discord.ext import commands


# Store Flask app for cross-module access
_flask_app = None
def set_flask_app(app):
    global _flask_app
    _flask_app = app
    return _flask_app

# Modular Imports
from modules.discord_bot.background_tasks import run_background_tasks
from modules.discord_bot.event_handlers import register_event_handlers
from modules.discord_bot.helpers.error_handler import setup_error_handler
from modules.discord_bot.message_handlers import handle_on_message

# Optional Modular Features

from modules.discord_bot.events.advanced_events import register_advanced_events

# Flask Blueprint
discord_bot_bp = Blueprint("discord_bot", __name__)

# Bot Setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix=os.getenv('PREFIX','!'), intents=intents)

# Tentukan mode
FLASK_ENV = os.getenv("FLASK_ENV", "production").lower()

# Ambil token sesuai mode
if FLASK_ENV == "development":
    BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN_LOCAL")
else:
    BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")


@discord_bot_bp.route("/start-bot")
def start_bot():
    if not bot.is_closed():
        return "🤖 Bot sudah berjalan."

    if not BOT_TOKEN:
        return f"❌ Token bot untuk mode {FLASK_ENV} tidak tersedia.", 500

    # Set Flask App agar bisa diakses modul lain
    set_flask_app(current_app)

    # Start bot di asyncio loop
    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(BOT_TOKEN))
    return f"✅ Bot dimulai dalam mode {FLASK_ENV}."


@discord_bot_bp.route("/ping", methods=["GET"])
def ping():
    current_app.logger.info("💓 Ping dari UptimeRobot diterima.")
    return jsonify({"status": "alive"})


@bot.event
async def on_ready():
    logging.info(f"✅ Bot berhasil login sebagai {bot.user} (ID: {bot.user.id})")
    logging.info(f"🌐 Mode: {FLASK_ENV}")

    # Jalankan background task
    run_background_tasks(bot)

    # Daftarkan semua handler utama & lanjutan
    register_event_handlers(bot)
    register_advanced_events(bot)
    # Heartbeat logger (Render logs)
    async def heartbeat_logger():
        import asyncio, json, time, os
        while True:
            try:
                payload = {
                    "ts": int(time.time()),
                    "user": str(bot.user) if bot.user else None,
                    "guilds": [g.id for g in bot.guilds],
                }
                print("[HEARTBEAT]", payload)
                os.makedirs('data', exist_ok=True)
                with open('data/heartbeat.json','w',encoding='utf-8') as fh:
                    fh.write(json.dumps(payload))
            except Exception as _hb_err:
                print("[HEARTBEAT][ERR]", _hb_err)
            await asyncio.sleep(int(os.getenv("HEARTBEAT_INTERVAL","60")))
    from modules.discord_bot.cogs_loader import load_all_cogs

    # Daftarkan error handler
    setup_error_handler(bot)

    # Tambahkan handler pesan utama
    bot.add_listener(handle_on_message, "on_message")