from modules import utils
from modules.discord_bot import bot
from modules.database import init_db
import asyncio, os, time

# ✅ Panggil log_startup hanya satu kali
utils.log_startup()

async def main():
    await init_db()
    utils.keep_alive()
    await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except Exception as e:
            print(f"[❌ ERROR] {e}")
            time.sleep(5)
            print("🔁 Restarting...")
