import discord
import os
import json
from discord.ext import commands

from modules.phishing_filter import (
    STATIC_KEYWORDS,
    BLACKLISTED_KEYWORDS,
    is_whitelisted,
    scan_image_for_phishing
)
from modules.logger import send_log_embed, notify_to_ngobrol
from modules.utils import app
from modules.database import init_db, save_log

# === Config & Setting ===
BAN_LOG_CHANNEL_NAMES = [
    "log-satpam-chat",
    "log-botphising",
    "mod-command"
]

def load_settings():
    try:
        with open("settings.json", "r") as f:
            return json.load(f)
    except:
        return {"AUTO_BAN_ENABLED": True}

def save_settings(settings):
    with open("settings.json", "w") as f:
        json.dump(settings, f, indent=2)

settings = load_settings()
AUTO_BAN_ENABLED = settings.get("AUTO_BAN_ENABLED", True)

# === Discord Bot Setup ===
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
notified_channels = set()  # mencegah spam startup

# === Fungsi Kirim Embed ke Beberapa Channel Log ===
async def log_ban_to_channels(bot, message, reason, ocr_text):
    embed = await send_log_embed(bot, message, reason, ocr_text, send=False)
    for ch in bot.get_all_channels():
        if ch.name in BAN_LOG_CHANNEL_NAMES:
            try:
                await ch.send(embed=embed)
            except Exception as e:
                print(f"❌ Gagal kirim ke #{ch.name}:", e)

# === Event Bot ===
@bot.event
async def on_ready():
    await init_db()
    print(f"✅ Bot aktif sebagai {bot.user}")
    for ch in bot.get_all_channels():
        if ch.name == "mod-command" and ch.id not in notified_channels:
            try:
                await ch.send("🟢 Bot aktif dan online!")
                notified_channels.add(ch.id)
            except Exception as e:
                print("❌ Gagal kirim pesan ke mod-command:", e)

@bot.event
async def on_message(message):
    global AUTO_BAN_ENABLED
    if message.author.bot:
        return

    reason, ocr_text = None, ""
    content = message.content.lower()

    if any(k in content for k in STATIC_KEYWORDS + BLACKLISTED_KEYWORDS) and not is_whitelisted(content):
        reason = "Phishing / scam detected via keyword"

    ocr_flag, ocr_text = await scan_image_for_phishing(message)
    if ocr_flag:
        reason = "Phishing via image (OCR)"

    if reason and AUTO_BAN_ENABLED:
        try:
            await message.delete()
            await message.guild.ban(message.author, reason=reason)
            await save_log(str(message.author.id), str(message.author), reason, message.content)
            await log_ban_to_channels(bot, message, reason, ocr_text)
            await notify_to_ngobrol(message)
            app.config["phishing_count"] += 1
        except Exception as e:
            print("❌ Gagal ban user:", e)

    app.config["messages_checked"] += 1
    await bot.process_commands(message)

# === Command Bot ===
@bot.command()
@commands.has_permissions(administrator=True)
async def servers(ctx):
    info = "\n".join([f"{g.name} - {g.member_count} anggota" for g in bot.guilds])
    await ctx.send(f"```{info}```")

# === Untuk manual run (opsional)
def run_bot():
    bot.run(os.getenv("DISCORD_TOKEN"))
