from flask import Blueprint
logger_bp = Blueprint("logger", __name__)

import discord, datetime

async def send_log_embed(bot, message, reason, ocr_text=""):
    embed = discord.Embed(title="🚨 Deteksi Phishing / AutoBan",
        description=f"👤 **User:** {message.author}\n📢 **Channel:** {message.channel.mention}\n🛑 **Alasan:** {reason}",
        color=discord.Color.red())
    embed.add_field(name="Isi Pesan", value=f"```{message.content}```", inline=False)
    if ocr_text:
        embed.add_field(name="OCR Deteksi Gambar", value=f"```{ocr_text[:500]}```", inline=False)
    embed.set_footer(text=f"SatpamBot | {datetime.datetime.now():%d %b %Y %H:%M}")
    for name in ["log-satpam-chat", "log-botphising", "mod-command"]:
        ch = discord.utils.get(message.guild.text_channels, name=name)
        if ch:
            await ch.send(embed=embed)

async def notify_to_ngobrol(message):
    ngobrol_ch = discord.utils.get(message.guild.text_channels, name="💬︲ngobrol")
    if ngobrol_ch:
        embed = discord.Embed(
            title="💀 Pengguna Terkick SatpamBot",
            description=f"{message.author.mention} telah dibanned karena link mencurigakan.",
            color=discord.Color.orange()
        )
        embed.set_footer(text="🧹 Dibersihkan oleh SatpamBot")
        try:
            await ngobrol_ch.send(embed=embed)
            sticker = discord.utils.get(message.guild.stickers, name="FibiLaugh")
            if sticker:
                await ngobrol_ch.send(sticker=sticker)
        except Exception as e:
            print("❌ Gagal kirim ke #💬︲ngobrol:", e)