from flask import Blueprint
import discord
import datetime

logger_bp = Blueprint("logger", __name__)

# ===== Kirim log embed ke channel log
async def send_log_embed(ctx_or_msg, reason, ocr_text=""):
    try:
        # Deteksi apakah ctx atau message
        if isinstance(ctx_or_msg, discord.Message):
            author = ctx_or_msg.author
            channel = ctx_or_msg.channel
            content = ctx_or_msg.content
            guild = ctx_or_msg.guild
        else:
            author = ctx_or_msg.author
            channel = ctx_or_msg.channel
            content = ctx_or_msg.message.content
            guild = ctx_or_msg.guild

        embed = discord.Embed(
            title="🚨 Aktivitas SatpamBot",
            description=(
                f"👤 **User:** {author} (`{author.id}`)\n"
                f"📢 **Channel:** {channel.mention}\n"
                f"🛠️ **Aksi:** {reason}"
            ),
            color=discord.Color.red()
        )

        if content:
            embed.add_field(name="Isi Pesan", value=f"```{content[:500]}```", inline=False)

        if ocr_text:
            embed.add_field(name="OCR Deteksi Gambar", value=f"```{ocr_text[:500]}```", inline=False)

        embed.set_footer(text=f"SatpamBot | {datetime.datetime.now():%d %b %Y %H:%M}")

        for name in ["log-satpam-chat", "log-botphising", "mod-command"]:
            ch = discord.utils.get(guild.text_channels, name=name)
            if ch:
                await ch.send(embed=embed)

    except Exception as e:
        print(f"❌ Gagal kirim log embed: {e}")

# ===== Kirim notifikasi ke channel #💬︲ngobrol
async def notify_to_ngobrol(message):
    try:
        ngobrol_ch = discord.utils.get(message.guild.text_channels, name="💬︲ngobrol")
        if not ngobrol_ch:
            ngobrol_ch = message.guild.get_channel(886534544688308265)  # Fallback ID

        if not ngobrol_ch:
            print("❌ Channel #💬︲ngobrol tidak ditemukan.")
            return

        embed = discord.Embed(
            title="💀 Pengguna Terkick SatpamBot",
            description=f"{message.author.mention} telah dibanned karena mengirim link mencurigakan.",
            color=discord.Color.orange()
        )
        embed.set_footer(text="🧹 Dibersihkan oleh SatpamBot")
        embed.timestamp = datetime.datetime.utcnow()

        await ngobrol_ch.send(embed=embed)

        # Kirim sticker "FibiLaugh" jika ada
        sticker = discord.utils.get(message.guild.stickers, name="FibiLaugh")
        if sticker:
            await ngobrol_ch.send(sticker=sticker)

    except Exception as e:
        print("❌ Gagal kirim ke #💬︲ngobrol:", e)
