import os
import json
import datetime
import asyncio
import discord
from discord.ext import commands, tasks
from flask import Blueprint, session

from modules.phishing_filter import (
    STATIC_KEYWORDS,
    BLACKLISTED_KEYWORDS,
    is_whitelisted,
    scan_image_for_phishing
)
from modules.logger import send_log_embed, notify_to_ngobrol
from modules.utils import START_TIME
from modules.database import init_db, save_log

# === Blueprint
discord_bot_bp = Blueprint("discord_bot", __name__)

# === Config
BAN_LOG_CHANNEL_NAMES = ["log-satpam-chat", "log-botphising", "mod-command"]
MOD_COMMAND_CHANNEL_ID = 936690788946030613

# === Load settings.json
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

# === Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)
notified_channels = set()
active_polls = {}

# === Flask app reference injection
flask_app = None

def set_flask_app(app):
    global flask_app
    flask_app = app
    with app.app_context():
        app.config.setdefault("messages_checked", 0)
        app.config.setdefault("phishing_count", 0)

# === Events
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="Menjaga server dari scam"), status=discord.Status.online)
    await init_db()
    print(f"\u2705 Bot aktif sebagai {bot.user}")

    if not check_dashboard_commands.is_running():
        check_dashboard_commands.start()

    if flask_app:
        with flask_app.app_context():
            flask_app.config.setdefault("messages_checked", 0)
            flask_app.config.setdefault("phishing_count", 0)

    try:
        for ch in bot.get_all_channels():
            if ch.name == "mod-command" and ch.id not in notified_channels:
                await ch.send(f"\U0001f7e2 Bot aktif sebagai **{bot.user}** pada `{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}`\nVersi commit: `bb88d91`")
                notified_channels.add(ch.id)
    except Exception as e:
        print("\u274c Gagal kirim pesan ke mod-command:", e)

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
            await notify_to_ngobrol(message)
            if flask_app:
                with flask_app.app_context():
                    flask_app.config["phishing_count"] = flask_app.config.get("phishing_count", 0) + 1
        except Exception as e:
            print("\u274c Gagal ban user:", e)

    if flask_app:
        with flask_app.app_context():
            flask_app.config["messages_checked"] = flask_app.config.get("messages_checked", 0) + 1
    await bot.process_commands(message)

# === Commands
@bot.command()
@commands.has_permissions(administrator=True)
async def servers(ctx):
    info = "\n".join([f"{g.name} - {g.member_count} anggota" for g in bot.guilds])
    await ctx.send(f"```{info}```")

@bot.command(name="status")
async def status(ctx):
    uptime = datetime.datetime.utcnow() - START_TIME
    embed = discord.Embed(title="\ud83d\udcca Bot Status", color=0x00ff00)
    embed.add_field(name="Servers", value=str(len(bot.guilds)))
    embed.add_field(name="Total Members", value=sum(g.member_count for g in bot.guilds))
    embed.add_field(name="Uptime", value=str(uptime).split(".")[0])
    await ctx.send(embed=embed)

@bot.command(name="buatrole")
@commands.has_role("Moderator")
async def buatrole(ctx, nama: str, warna: str = "#3498db"):
    color = discord.Color(int(warna.strip("#"), 16))
    await ctx.guild.create_role(name=nama, color=color)
    await ctx.send(embed=discord.Embed(title="\u2705 Role Dibuat", description=f"Role `{nama}` berhasil dibuat.", color=color))

@bot.command(name="buatchannel")
@commands.has_role("Moderator")
async def buatchannel(ctx, nama: str, tipe: str = "text"):
    if tipe == "voice":
        await ctx.guild.create_voice_channel(nama)
    else:
        await ctx.guild.create_text_channel(nama)
    await ctx.send(embed=discord.Embed(title="\u2705 Channel Dibuat", description=f"Channel `{nama}` berhasil dibuat."))

@bot.command(name="poll")
async def poll(ctx, *, args):
    try:
        parts = args.split("|")
        if len(parts) < 3:
            await ctx.send("\u274c Format: `!poll Judul | Opsi1 | Opsi2 ... | [waktu: 5m/1h/1d]`")
            return
        title = parts[0].strip()
        options = [opt.strip() for opt in parts[1:] if opt.strip() and not opt.strip().endswith(("m", "h", "d"))]
        if len(options) > 10:
            await ctx.send("\u274c Maksimal 10 opsi.")
            return

        time_option = next((opt.strip() for opt in parts if opt.strip().endswith(("m", "h", "d"))), None)
        duration = None
        if time_option:
            unit = time_option[-1]
            number = int(time_option[:-1])
            duration = number * 60 if unit == "m" else number * 3600 if unit == "h" else number * 86400

        emoji_list = ['1\u20e3','2\u20e3','3\u20e3','4\u20e3','5\u20e3','6\u20e3','7\u20e3','8\u20e3','9\u20e3','\ud83d\udd1f']
        desc = "\n".join([f"{emoji_list[i]} {opt}" for i, opt in enumerate(options)])
        embed = discord.Embed(title=title, description=desc, color=0x7289DA)
        embed.set_footer(text=f"Voting dimulai oleh: {ctx.author.display_name}")
        msg = await ctx.send(embed=embed)
        for i in range(len(options)):
            await msg.add_reaction(emoji_list[i])

        if duration:
            active_polls[msg.id] = (ctx.channel.id, msg.id)
            await asyncio.sleep(duration)
            message = await ctx.channel.fetch_message(msg.id)
            counts = [(reaction.emoji, reaction.count - 1) for reaction in message.reactions if reaction.emoji in emoji_list]
            counts.sort(key=lambda x: x[1], reverse=True)
            result_desc = "\n".join([f"{emoji}: {count} vote" for emoji, count in counts])
            result_embed = discord.Embed(title=f"Hasil Poll: {title}", description=result_desc, color=0x43B581)
            await ctx.send(embed=result_embed)
            del active_polls[msg.id]
    except Exception as e:
        await ctx.send(f"\u274c Error: {e}")

@bot.command(name="closepoll")
async def closepoll(ctx):
    try:
        found = None
        for mid, (cid, _) in active_polls.items():
            if cid == ctx.channel.id:
                found = mid
                break
        if not found:
            await ctx.send("\u26a0\ufe0f Tidak ada polling aktif di channel ini.")
            return
        message = await ctx.channel.fetch_message(found)
        emoji_list = ['1\u20e3','2\u20e3','3\u20e3','4\u20e3','5\u20e3','6\u20e3','7\u20e3','8\u20e3','9\u20e3','\ud83d\udd1f']
        counts = [(reaction.emoji, reaction.count - 1) for reaction in message.reactions if reaction.emoji in emoji_list]
        counts.sort(key=lambda x: x[1], reverse=True)
        result_desc = "\n".join([f"{emoji}: {count} vote" for emoji, count in counts])
        result_embed = discord.Embed(title="\ud83d\udcca Hasil Poll (Ditutup Manual)", description=result_desc, color=0xffcc00)
        await ctx.send(embed=result_embed)
        del active_polls[found]
    except Exception as e:
        await ctx.send(f"\u274c Gagal menutup polling: {e}")

# === Background Task (inject context safely)
@tasks.loop(seconds=10)
async def check_dashboard_commands():
    await bot.wait_until_ready()
    if not flask_app:
        return

    with flask_app.app_context():
        with flask_app.test_request_context():
            try:
                role_data = session.get("create_role_data")
                if role_data:
                    guild = discord.utils.get(bot.guilds)
                    if not guild:
                        return
                    color = discord.Color(int(role_data['color'].lstrip('#'), 16))
                    icon_data = None
                    if role_data['icon']:
                        path = os.path.join("satpambot_monitor_plus_modern", "static", "uploads", role_data['icon'])
                        with open(path, "rb") as f:
                            icon_data = f.read()
                    await guild.create_role(name=role_data['name'], color=color, icon=icon_data)
                    print(f"[\u2705 BOT] Role '{role_data['name']}' dibuat dari dashboard.")
                    session.pop("create_role_data")

                channel_data = session.get("create_channel_data")
                if channel_data:
                    guild = discord.utils.get(bot.guilds)
                    if channel_data['type'] == "text":
                        await guild.create_text_channel(channel_data['name'])
                    else:
                        await guild.create_voice_channel(channel_data['name'])
                    print(f"[\u2705 BOT] Channel '{channel_data['name']}' dibuat.")
                    session.pop("create_channel_data")
            except Exception as e:
                print("[\u274c BOT ERROR] Saat buat role/channel:", e)

# === Bot runner
def run_bot():
    bot.run(os.getenv("DISCORD_TOKEN"))
