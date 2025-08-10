import re
import discord
from discord.ext import commands

# === CONFIG ===
INVITE_REGEX = re.compile(
    r"(?:https?:\/\/)?(?:www\.)?(?:discord(?:\.gg|(?:app)?\.com\/invite)\/)([A-Za-z0-9\-]+)",
    re.IGNORECASE,
)
ALLOW_OWN_SERVER_INVITES = True          # True = izinkan undangan ke server ini (whitelist by guild_id)
GUILD_ID_WHITELIST = None                # set ke ID server kamu (int) kalau mau whitelist undangan ke server sendiri
BAN_DELETE_MESSAGE_DAYS = 7              # hapus semua pesan user 7 hari terakhir saat diban (0-7)

NOTICE_AFTER_BAN = "🚫 {user} telah dibanned karena mengirim undangan NSFW."

def _is_nsfw_invite(invite: discord.Invite) -> bool:
    """True jika undangan mengarah ke kanal/guild NSFW."""
    # Kanal NSFW?
    try:
        if invite.channel and getattr(invite.channel, "nsfw", False):
            return True
    except Exception:
        pass
    # Level NSFW guild (partial guild biasanya punya nsfw_level)
    try:
        nsfw_level = str(getattr(invite.guild, "nsfw_level", "") or "").lower()
        # nilai umum: 'default', 'explicit', 'safe', 'age_restricted'
        if nsfw_level in {"explicit", "age_restricted"}:
            return True
    except Exception:
        pass
    return False

class AntiInvite(commands.Cog):
    """Autoban pengguna yang mengirim undangan Discord NSFW. Undangan lain dibiarkan."""
    def __init__(self, bot: commands.Bot, guild_id: int | None = GUILD_ID_WHITELIST):
        self.bot = bot
        self.guild_id = guild_id

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Cari semua kode undangan di pesan
        codes = [m.group(1) for m in INVITE_REGEX.finditer(message.content or "")]
        if not codes:
            return

        # Lewatkan moderator/admin
        perms = message.author.guild_permissions
        if perms.manage_guild or perms.manage_messages or perms.administrator:
            return

        # Cek setiap kode
        for code in set(codes):
            try:
                invite = await self.bot.fetch_invite(code, with_counts=False)
            except Exception:
                continue

            # Biarkan undangan ke server sendiri (opsional)
            if ALLOW_OWN_SERVER_INVITES and self.guild_id:
                try:
                    if invite.guild and invite.guild.id == self.guild_id:
                        continue
                except Exception:
                    pass

            if _is_nsfw_invite(invite):
                # AUTOBAN user dan hapus pesan beberapa hari terakhir
                try:
                    await message.guild.ban(
                        message.author,
                        reason="Mengirim undangan Discord NSFW",
                        delete_message_days=max(0, min(7, int(BAN_DELETE_MESSAGE_DAYS))),
                    )
                except TypeError:
                    # fallback untuk kompatibilitas versi discord.py berbeda
                    try:
                        await message.author.ban(
                            reason="Mengirim undangan Discord NSFW",
                            delete_message_days=max(0, min(7, int(BAN_DELETE_MESSAGE_DAYS))),
                        )
                    except Exception:
                        pass
                except Exception:
                    pass

                # Coba kirim notifikasi singkat (abaikan error perms)
                try:
                    await message.channel.send(
                        NOTICE_AFTER_BAN.format(user=str(message.author)), delete_after=10
                    )
                except Exception:
                    pass
                return  # selesai setelah ban

async def setup(bot: commands.Bot):
    # Isi GUILD_ID_WHITELIST di atas bila ingin whitelist undangan ke server sendiri
    await bot.add_cog(AntiInvite(bot))
