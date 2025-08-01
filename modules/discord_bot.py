import discord, os, json
from discord.ext import commands
from modules.phishing_filter import STATIC_KEYWORDS, BLACKLISTED_KEYWORDS, is_whitelisted, scan_image_for_phishing
from modules.logger import send_log_embed, notify_to_ngobrol
from modules.utils import app
from modules.database import init_db, save_log

# === Load Settings ===
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

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await init_db()
    print(f"✅ Bot aktif sebagai {bot.user}")
    ch = discord.utils.get(bot.get_all_channels(), name="mod-command")
    if ch: await ch.send("🟢 Bot aktif dan online!")

@bot.event
async def on_message(message):
    global AUTO_BAN_ENABLED
    if message.author.bot: return

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
            await send_log_embed(bot, message, reason, ocr_text)
            await notify_to_ngobrol(message)
            app.config["phishing_count"] += 1
        except Exception as e:
            print("❌ Gagal ban user:", e)

    app.config["messages_checked"] += 1
    await bot.process_commands(message)

@bot.command()
@commands.has_permissions(administrator=True)
async def servers(ctx):
    info = "\n".join([f"{g.name} - {g.member_count} anggota" for g in bot.guilds])
    await ctx.send(f"```{info}```")

def run_bot():
    bot.run(os.getenv("DISCORD_TOKEN"))
