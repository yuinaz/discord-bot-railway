import os
import json
import asyncio
import logging
import sys
from flask import Flask, request, redirect
from dotenv import load_dotenv
from modules.utils import get_current_theme

# === Load .env
load_dotenv()

# === Setup Logging
class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            self.stream.write(msg + self.terminator)
            self.flush()
        except UnicodeEncodeError:
            record.msg = record.msg.encode("ascii", errors="ignore").decode()
            super().emit(record)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    handlers=[
        logging.FileHandler("error.log", encoding="utf-8"),
        SafeStreamHandler(sys.stdout)
    ]
)

def safe_log(msg, level="info"):
    try:
        if level == "error":
            logging.error(msg)
        elif level == "warning":
            logging.warning(msg)
        else:
            logging.info(msg)
    except UnicodeEncodeError:
        fallback = msg.encode("ascii", "ignore").decode()
        logging.info(fallback)

# === Init Flask
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("SECRET_KEY", "defaultsecret")
app.config["DEBUG"] = True  # Matikan jika produksi

# === Import Blueprints
from modules.backup import backup_bp
from modules.dashboard import dashboard_bp
from modules.database import database_bp
from modules.discord_bot import discord_bot_bp, bot, set_flask_app
from modules.editor import editor_bp
from modules.gpt_chat import gpt_chat_bp
from modules.logger import logger_bp
from modules.notify_ngobrol_ban import notify_ngobrol_ban_bp
from modules.oauth import oauth_bp
from modules.phishing_filter import phishing_filter_bp
from modules.updater import updater_bp
from modules.utils import utils_bp
from modules.whitelist import whitelist_bp

# === Register semua Blueprints
app.register_blueprint(backup_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(database_bp)
app.register_blueprint(discord_bot_bp)
app.register_blueprint(editor_bp)
app.register_blueprint(gpt_chat_bp)
app.register_blueprint(logger_bp)
app.register_blueprint(notify_ngobrol_ban_bp)
app.register_blueprint(oauth_bp, url_prefix="/")  # ✅ Penting untuk /login dan /logout
app.register_blueprint(phishing_filter_bp)
app.register_blueprint(updater_bp)
app.register_blueprint(utils_bp)
app.register_blueprint(whitelist_bp)

# === Inject Flask ke Discord bot
set_flask_app(app)

# === Redirect root ke login
@app.route("/")
def root():
    return redirect("/login")

# === Theme switcher
@app.route("/theme")
def theme():
    theme_name = request.args.get("set")
    if theme_name:
        try:
            os.makedirs("config", exist_ok=True)
            with open("config/theme.json", "w", encoding="utf-8") as f:
                json.dump({"theme": theme_name}, f)
        except Exception as e:
            logging.error("❌ Gagal menyimpan tema:", exc_info=True)
    return redirect(request.referrer or "/")

# === 404 Error
@app.errorhandler(404)
def not_found(e):
    logging.warning(f"404 Not Found: {request.path}")
    return "❌ Halaman tidak ditemukan. Cek apakah route atau nama file HTML valid.", 404

# === Global Error
@app.errorhandler(Exception)
def handle_exception(e):
    logging.error("❌ Unhandled Exception:", exc_info=True)
    return "❌ Terjadi error internal di server. Silakan cek log.", 500

# === Jalankan Bot Discord Async
async def run_bot_async():
    try:
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            raise Exception("DISCORD_TOKEN tidak ditemukan di .env")
        safe_log("🔁 Menjalankan Discord bot...")
        await bot.start(token)
    except Exception:
        logging.error("❌ Bot gagal dijalankan:", exc_info=True)

# === Jalankan Flask + Discord
async def start_all():
    asyncio.create_task(run_bot_async())

    try:
        from hypercorn.asyncio import serve
        from hypercorn.config import Config

        if os.getenv("RENDER") == "true" and not os.getenv("PORT"):
            os.environ["PORT"] = "8080"

        config = Config()
        port = os.getenv("PORT", "8080")
        config.bind = [f"0.0.0.0:{port}"]

        safe_log("✅ Menjalankan Flask server via Hypercorn...")
        await serve(app, config)

    except ModuleNotFoundError:
        safe_log("⚠️ Hypercorn tidak ditemukan. Menjalankan Flask dev server fallback.", level="warning")
        port = int(os.getenv("PORT", "8080"))
        app.run(host="0.0.0.0", port=port, debug=False)

    except OSError as e:
        if e.errno == 98:
            safe_log("⚠️ Port sudah digunakan. Menjalankan Flask dev server fallback.", level="warning")
            app.run(host="0.0.0.0", port=int(port), debug=False)
        else:
            raise

# === Entry Point
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(start_all())
    except KeyboardInterrupt:
        safe_log("⛔ Dihentikan oleh pengguna (CTRL+C)", level="warning")
    finally:
        async def shutdown():
            if not bot.is_closed():
                safe_log("🛑 Menutup bot...")
                await bot.close()
        try:
            loop.run_until_complete(shutdown())
        except Exception:
            logging.error("❌ Gagal menutup bot:", exc_info=True)
        finally:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            try:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except:
                pass
            loop.close()
            safe_log("✅ Bot & server dihentikan dengan bersih.")
