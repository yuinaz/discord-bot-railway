# run.py

from main import app

if __name__ == "__main__":
    # Jalankan dari entry run.py jika diperlukan
    from modules.discord_bot.discord_bot import start_bot
    start_bot(app)
