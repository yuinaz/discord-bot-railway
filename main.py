import asyncio
import os
from dotenv import load_dotenv

# === Load environment ===
load_dotenv()

# === Import dari modul internal ===
from modules.discord_bot import bot
from modules.utils import keep_alive, log_startup
from modules.database import init_db
from modules.dashboard import app

async def main():
    # Inisialisasi database log async
    await init_db()

    # Aktifkan web Flask + heartbeat
    keep_alive()
    log_startup()

    # Ambil token dari .env
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("❌ DISCORD_TOKEN belum diatur di .env")

    print(f"🔐 Token dimuat, panjang: {len(token)} karakter")  # Tambahan log penting untuk debug

    # Jalankan bot Discord
    await bot.start(token)

# === Eksekusi utama ===
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[❌ ERROR] {e}")
