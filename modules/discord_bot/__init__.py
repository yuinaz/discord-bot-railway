from modules.discord_bot.helpers.env_loader import load_env

# ✅ Load environment dulu
mode = load_env()
print(f"Bot berjalan dalam mode: {mode}")

from flask import Blueprint

# Blueprint utama untuk semua endpoint Discord bot
discord_bot_bp = Blueprint("discord_bot", __name__)

# Import dan setup komponen bot
from .discord_bot import bot, set_flask_app
from .routes.status_route import register_status_routes

# Gabungkan semua route tambahan langsung ke discord_bot_bp
register_status_routes(discord_bot_bp)

# Fungsi untuk me-load semua command yang dimodularisasi

# Optional: load commands dynamically (placeholder)
def load_commands():
    try:
        from .cogs_loader import load_all_cogs
        import asyncio
        asyncio.get_event_loop().create_task(load_all_cogs(bot))
    except Exception as e:
        print("[init] load_commands skipped:", e)


# === Provide run_bot() for app.py background thread ===
def run_bot():
    import os, asyncio
    from .discord_bot import bot  # uses same instance
    env = os.getenv("FLASK_ENV", "production").lower()
    token = os.getenv("DISCORD_BOT_TOKEN_LOCAL") if env == "development" else os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("[run_bot] ❌ Missing DISCORD_BOT_TOKEN" + ("_LOCAL" if env=="development" else ""))
        return
    print(f"[run_bot] Starting Discord bot in FLASK_ENV={env}")
    asyncio.run(bot.start(token))
