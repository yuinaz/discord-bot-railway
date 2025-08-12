
import sqlite3, os
DB_PATH = os.getenv("DB_PATH", "superadmin.db")

def _db_upsert_guild(guild):
    try:
        gid = str(guild.id)
        name = guild.name
        icon_url = str(guild.icon.url) if getattr(guild, "icon", None) else None
        mc = getattr(guild, "member_count", None) or 0
        ja = None
        try:
            me = guild.me
            if getattr(me, "joined_at", None):
                ja = me.joined_at.isoformat()
        except Exception:
            pass
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_guilds (
                    guild_id TEXT PRIMARY KEY,
                    name TEXT,
                    member_count INTEGER,
                    icon_url TEXT,
                    joined_at TEXT
                )
            """)
            conn.execute("""
                INSERT INTO bot_guilds (guild_id, name, member_count, icon_url, joined_at)
                VALUES (?,?,?,?,?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    name=excluded.name,
                    member_count=excluded.member_count,
                    icon_url=excluded.icon_url,
                    joined_at=COALESCE(bot_guilds.joined_at, excluded.joined_at)
            """, (gid, name, mc, icon_url, ja))
            conn.commit()
    except Exception as e:
        print("[guilds] upsert fail", e)

def _db_remove_guild(guild_id: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM bot_guilds WHERE guild_id=?", (str(guild_id),))
            conn.commit()
    except Exception as e:
        print("[guilds] remove fail", e)

from .helpers.once import once
# modules/discord_bot/events/event_handler.py
import discord
from datetime import datetime
from discord.ext import commands

import aiohttp
INGEST_URL = "https://satpambot.onrender.com/ingest/ban"
INGEST_TOKEN = "Musedash123"

async def _post_ingest(payload):
    try:
        async with aiohttp.ClientSession() as sess:
            await sess.post(INGEST_URL, json=payload, headers={"X-INGEST-TOKEN": INGEST_TOKEN})
    except Exception as e:
        print("[ingest] failed", e)


# === Kirim log ke channel #log-botphising (bot aktif) ===
async def notify_bot_active(guild: discord.Guild, bot_name: str):
    log_channel = discord.utils.get(guild.text_channels, name="log-botphising")
    if log_channel:
        await log_channel.send(
            f"🟢 Bot aktif sebagai **{bot_name}** pada {datetime.now():%Y-%m-%d %H:%M:%S}"
        )

# === Kirim embed banned ke channel #log-satpam-chat ===
async def notify_ban_embed(guild: discord.Guild, user: discord.User, reason: str):
    log_channel = discord.utils.get(guild.text_channels, name="log-satpam-chat")
    if log_channel:
        embed = discord.Embed(
            title="🚫 Pengguna Terbanned",
            description=f"{user.mention} telah dibanned.\n**Alasan:** {reason}",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="SatpamBot Security")
        await log_channel.send(embed=embed)

# === Kirim notifikasi banned + sticker FibiLaugh ke #💬︲ngobrol ===
async def notify_to_ngobrol(guild: discord.Guild, user: discord.User, reason: str):
    ngobrol_ch = discord.utils.get(guild.text_channels, name="💬︲ngobrol")
    if not ngobrol_ch:
        ngobrol_ch = guild.get_channel(886534544688308265)  # ID fallback

    if ngobrol_ch:
        embed = discord.Embed(
            title="💀 Pengguna Terkick SatpamBot",
            description=f"{user.mention} telah dibanned karena {reason}.",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="🧹 Dibersihkan oleh SatpamBot")
        await ngobrol_ch.send(embed=embed)

        # Kirim sticker FibiLaugh jika ada
        sticker = discord.utils.get(guild.stickers, name="FibiLaugh")
        if sticker:
            await ngobrol_ch.send(stickers=[sticker])


# ==============================
# EVENT HANDLER BOT
# ==============================
async def on_ready(bot: commands.Bot):
    print(f"✅ Bot login sebagai {bot.user}")
    for guild in bot.guilds:
        await notify_bot_active(guild, bot.user.name)

async def on_member_ban(guild: discord.Guild, user: discord.User):
    reason = "Pelanggaran aturan"
    await notify_ban_embed(guild, user, reason)
    await notify_to_ngobrol(guild, user, reason)


# === Registrar untuk mendaftarkan event ke bot ===
def register_event_handlers(bot):
    import asyncio
    @bot.event
    async def on_ready():
        try:
            # Kirim tanda bot aktif ke setiap guild (jika channel ada)
            for guild in bot.guilds:
                try:
                    await notify_bot_active(guild, str(bot.user))
                except Exception:
                    pass
            print("[event_handlers] on_ready sent notify_bot_active")
        except Exception as e:
            print("[event_handlers] on_ready error", e)

    @bot.event
    async def on_member_ban(guild, user):
        try:
            await notify_ban_embed(guild, user, reason="Pelanggaran aturan")
        try:
            await _post_ingest({"action":"ban","user_id": str(user.id), "username": str(user), "guild_id": str(guild.id)})
        except Exception as e:
            print("[event_handlers] ingest ban error", e)
        
        except Exception as e:
            print("[event_handlers] on_member_ban error", e)

    @bot.event
    async def on_member_unban(guild, user):
        try:
            await notify_unban_embed(guild, user, moderator_name="Moderator", reason="Unban manual")
        try:
            await _post_ingest({"action":"unban","user_id": str(user.id), "username": str(user), "guild_id": str(guild.id)})
        except Exception as e:
            print("[event_handlers] ingest unban error", e)
        
        except Exception as e:
            # tidak fatal kalau gagal kirim embed
            print("[event_handlers] on_member_unban error", e)

    return bot

pass
        m = RE_UNBAN.search(msg.content or "")
        if m:
            user_id, guild_id = m.group(1), m.group(2)
            await _post_ingest({"action":"unban","user_id":user_id,"guild_id":guild_id})


import os, re
LOG_BAN_CHANNEL_NAME = os.getenv("LOG_BAN_CHANNEL_NAME", "log-satpam")
LOG_BAN_CHANNEL_ID = int(os.getenv("LOG_BAN_CHANNEL_ID", "0"))

def _first_id_from_text(text: str | None):
    if not text: return None
    m = re.search(r"(\d{17,20})", text)
    return m.group(1) if m else None

def _extract_user_id_from_message(msg):
    # Try regular content
    uid = _first_id_from_text(getattr(msg, "content", ""))
    # Inspect embeds (Carl-bot style)
    for emb in getattr(msg, "embeds", []) or []:
        for part in [getattr(emb, "description", None), getattr(emb, "title", None),
                     getattr(getattr(emb, "footer", None), "text", None), 
                     getattr(getattr(emb, "author", None), "name", None)]:
            uid = uid or _first_id_from_text(part)
    return uid

async def on_message_parser(msg):
    # Filter channel by name or explicit ID (if provided)
    if LOG_BAN_CHANNEL_ID:
        if getattr(getattr(msg, "channel", None), "id", None) != LOG_BAN_CHANNEL_ID:
            return
    else:
        if getattr(getattr(msg, "channel", None), "name", "") != LOG_BAN_CHANNEL_NAME:
            return

    # Determine action from text or embed title
    text = (msg.content or "").lower()
    titles = []
    for emb in getattr(msg, "embeds", []) or []:
        if getattr(emb, "title", None):
            titles.append(emb.title.lower())
        if getattr(emb, "description", None):
            text += " " + emb.description.lower()
    is_ban = ("member banned" in " ".join(titles)) or (" banned" in text)
    is_unban = ("member unbanned" in " ".join(titles)) or (" unbanned" in text) or ("unban" in text)

    uid = _extract_user_id_from_message(msg)
    if not uid:
        return

    if is_ban and not is_unban:
        await _post_ingest({"action":"ban","user_id": uid, "guild_id": str(getattr(getattr(msg,'guild',None),'id',0))})
    elif is_unban:
        await _post_ingest({"action":"unban","user_id": uid, "guild_id": str(getattr(getattr(msg,'guild',None),'id',0))})


@bot.event
async def on_guild_join(guild):
    _db_upsert_guild(guild)

@bot.event
async def on_guild_remove(guild):
    _db_remove_guild(guild.id)
