from .helpers.once import once
# modules/discord_bot/events/event_handler.py
import discord
from datetime import datetime
from discord.ext import commands

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
        except Exception as e:
            print("[event_handlers] on_member_ban error", e)

    @bot.event
    async def on_member_unban(guild, user):
        try:
            await notify_unban_embed(guild, user, moderator_name="Moderator", reason="Unban manual")
        except Exception as e:
            # tidak fatal kalau gagal kirim embed
            print("[event_handlers] on_member_unban error", e)

    return bot
