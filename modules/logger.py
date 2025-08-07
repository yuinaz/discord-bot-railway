from flask import Blueprint
import discord
import datetime

logger_bp = Blueprint("logger", __name__)

# === Konfigurasi nama-nama channel log
BAN_LOG_CHANNEL_NAMES = ["log-satpam-chat", "log-botphising", "mod-command"]

# ===== Kirim log embed ke channel log
async def send_log_embed(ctx_or_msg, reason, ocr_text=""):
    try:
        if isinstance(ctx_or_msg, discord.Message):
            author = ctx_or_msg.author
            channel = ctx_or_msg.channel
            content = ctx_or_msg.content
            guild = ctx_or_msg.guild
        elif hasattr(ctx_or_msg, 'author') and hasattr(ctx_or_msg, 'channel'):
            # Untuk command context
            author = ctx_or_msg.author
            channel = ctx_or_msg.channel
            content = ctx_or_msg.message.content if hasattr(ctx_or_msg, 'message') else ""
            guild = ctx_or_msg.guild
        elif isinstance(ctx_or_msg, discord.Member):
            # Jika hanya Member (tanpa channel atau ctx)
            author = ctx_or_msg
            channel = None
            content = ""
            guild = ctx_or_msg.guild
        else:
            print("❌ Objek tidak dikenali oleh send_log_embed.")
            return

        embed = discord.Embed(
            title="🚨 Aktivitas SatpamBot",
            description=(
                f"👤 **User:** {author} (`{author.id}`)\n"
                f"🛠️ **Aksi:** {reason}"
            ),
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )

        if content:
            embed.add_field(name="Isi Pesan", value=f"```{content[:500]}```", inline=False)

        if ocr_text:
            embed.add_field(name="OCR Deteksi Gambar", value=f"```{ocr_text[:500]}```", inline=False)

        embed.set_footer(text="SatpamBot | Log otomatis")

        # Kirim ke salah satu channel log
        for name in BAN_LOG_CHANNEL_NAMES:
            ch = discord.utils.get(guild.text_channels, name=name)
            if ch:
                await ch.send(embed=embed)
                break

    except Exception as e:
        print(f"❌ Gagal kirim log embed: {e}")

# ===== Kirim notifikasi ke channel #💬︲ngobrol
async def notify_to_ngobrol(message):
    try:
        ngobrol_ch = discord.utils.get(message.guild.text_channels, name="💬︲ngobrol")
        if not ngobrol_ch:
            ngobrol_ch = message.guild.get_channel(886534544688308265)  # Ganti dengan ID fallback jika perlu

        if not ngobrol_ch:
            print("❌ Channel #💬︲ngobrol tidak ditemukan.")
            return

        embed = discord.Embed(
            title="💀 Pengguna Terkick SatpamBot",
            description=f"{message.author.mention} telah dibanned karena mengirim link mencurigakan.",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text="🧹 Dibersihkan oleh SatpamBot")

        await ngobrol_ch.send(embed=embed)

        # Kirim sticker jika tersedia
        sticker = discord.utils.get(message.guild.stickers, name="FibiLaugh")
        if sticker:
            await ngobrol_ch.send(stickers=[sticker])

    except Exception as e:
        print("❌ Gagal kirim ke #💬︲ngobrol:", e)
