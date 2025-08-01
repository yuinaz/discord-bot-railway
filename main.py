import os
import asyncio
import threading
from dotenv import load_dotenv

# Load token & variabel dari .env
load_dotenv()

from modules import utils
from modules.discord_bot import bot
from modules.database import init_db

# Log saat startup
utils.log_startup()

# Jalankan Flask + Heartbeat di background thread
def start_flask_background():
    utils.keep_alive()

threading.Thread(target=start_flask_background, daemon=True).start()

# Main bot Discord
async def main():
    await init_db()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN tidak ditemukan di .env!")
        return
    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
