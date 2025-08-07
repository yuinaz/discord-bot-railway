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

# === Pastikan Folder & File Penting Ada ===
os.makedirs("data", exist_ok=True)
os.makedirs("backup", exist_ok=True)
os.makedirs("logs", exist_ok=True)
os.makedirs("config", exist_ok=True)

def ensure_file_exists(path, default_content):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(default_content, (dict, list)):
                json.dump(default_content, f)
            else:
                f.write(default_content)
        print(f"✅ {path} dibuat.")

ensure_file_exists("config/theme.json", {"theme": "default"})
ensure_file_exists("data/whitelist.json", [])
ensure_file_exists("logs/error.log", "")

# === Cek ENV
if not os.getenv("DISCORD_TOKEN"):
    print("❌ DISCORD_TOKEN tidak ditemukan di .env")
    exit(1)
if not os.getenv("SECRET_KEY"):
    print("❌ SECRET_KEY tidak ditemukan di .env")
    exit(1)

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
        logging.FileHandler("logs/error.log", encoding="utf-8"),
        SafeStreamHandler(sys.stdout)
    ]
)

def safe_log(msg, level="info"):
    try:
        if level == "error":
            logging.error(msg)
        elif level == "warning":
            logging.warning(msg)
        elif level == "critical":
            logging.critical(msg)
        else:
            logging.info(msg)
    except UnicodeEncodeError:
        fallback = msg.encode("ascii", "ignore").decode()
        logging.info(fallback)

# === Init Flask
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("SECRET_KEY", "defaultsecret")
app.config["DEBUG"] = os.getenv("DEBUG", "false").lower() == "true"

# === Inject fungsi tema ke template
app.jinja_env.globals['get_current_theme'] = get_current_theme

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

# === Register Blueprints
blueprints = {
    backup_bp: None,
    dashboard_bp: None,
    database_bp: None,
    discord_bot_bp: None,
    editor_bp: None,
    gpt_chat_bp: None,
    logger_bp: None,
    notify_ngobrol_ban_bp: None,
    oauth_bp: "/",
    phishing_filter_bp: None,
    updater_bp: None,
    utils_bp: None,
    whitelist_bp: None,
}
for bp, prefix in blueprints.items():
    app.register_blueprint(bp, url_prefix=prefix)

# === Inject Flask ke bot Discord
set_flask_app(app)

# === Route: Redirect root ke /login
@app.route("/")
def root():
    return redirect("/login")

# ✅ Route: Healthcheck untuk Render
@app.route("/healthcheck")
def healthcheck():
    return "✅ OK", 200

# === 404 Handler
@app.errorhandler(404)
def not_found(e):
    safe_log(f"404 Not Found: {request.path}", level="warning")
    return "❌ Halaman tidak ditemukan. Cek apakah route atau nama file HTML valid.", 404

# === Global Exception Handler
@app.errorhandler(Exception)
def handle_exception(e):
    safe_log("❌ Unhandled Exception:", level="error")
    return "❌ Terjadi error internal di server. Silakan cek log.", 500

# === Jalankan Bot Discord Async
async def run_bot_async():
    try:
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            raise Exception("DISCORD_TOKEN tidak ditemukan di .env")
        safe_log("🔁 Menjalankan Discord bot...")
        await bot.start(token)
        safe_log("⚠️ bot.start() selesai — kemungkinan token salah atau bot crash.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        safe_log(f"❌ Bot gagal dijalankan: {e}", level="error")

# === Jalankan Flask + Discord Bot
async def start_all():
    asyncio.create_task(run_bot_async())

    try:
        from hypercorn.asyncio import serve
        from hypercorn.config import Config

        port = os.getenv("PORT") or ("8080" if os.getenv("RENDER") == "true" else "5000")
        config = Config()
        config.bind = [f"0.0.0.0:{port}"]

        safe_log("✅ Menjalankan Flask server via Hypercorn...")
        await serve(app, config)
    except ModuleNotFoundError:
        safe_log("⚠️ Hypercorn tidak ditemukan. Menjalankan Flask dev server fallback.", level="warning")
        port = int(os.getenv("PORT", "8080"))
        app.run(host="0.0.0.0", port=port, debug=False)
        return
    except OSError as e:
        if e.errno == 98:
            safe_log("⚠️ Port sudah digunakan. Menjalankan Flask dev server fallback.", level="warning")
            app.run(host="0.0.0.0", port=int(port), debug=False)
            return
        else:
            raise

    # ✅ Cegah shutdown otomatis
    await asyncio.Event().wait()

# === Entry Point
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

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
            safe_log("❌ Gagal menutup bot:", level="error")
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
