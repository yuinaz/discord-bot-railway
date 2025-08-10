import re
import discord
from discord.ext import commands

INVITE_REGEX = re.compile(
    r"(?:https?:\/\/)?(?:www\.)?(?:discord(?:\.gg|(?:app)?\.com\/invite)\/)([A-Za-z0-9\-]+)",
    re.IGNORECASE,
)

# Konfigurasi
ALLOW_OWN_SERVER_INVITES = True  # True: undangan ke server ini (guild_id) tidak dihapus
GUILD_ID_WHITELIST = None        # ganti ke int ID server kamu, contoh: 123456789012345678

DELETE_REASON = "Menghapus undangan NSFW."
NOTICE_TEXT = "{mention} tautan undangan NSFW tidak diperbolehkan di sini."

def _is_nsfw_invite(invite: discord.Invite) -> bool:
    """Kembalikan True jika undangan mengarah ke kanal/guild NSFW."""
    # Kanal NSFW?
    try:
        if invite.channel and getattr(invite.channel, "nsfw", False):
            return True
    except Exception:
        pass
    # Level NSFW guild
    try:
        nsfw_level = str(getattr(invite.guild, "nsfw_level", "") or "").lower()
        # nilai umum: 'default', 'explicit', 'safe', 'age_restricted'
        if nsfw_level in {"explicit", "age_restricted"}:
            return True
    except Exception:
        pass
    return False

class AntiInvite(commands.Cog):
    """Blokir undangan Discord NSFW. Biarkan undangan lain lewat."""
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

        # Moderator dilewati
        perms = message.author.guild_permissions
        if perms.manage_guild or perms.manage_messages or perms.administrator:
            return

        # Cek setiap kode
        is_nsfw_found = False
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
                is_nsfw_found = True
                break

        if is_nsfw_found:
            try:
                await message.delete()
            except Exception:
                pass
            try:
                await message.channel.send(
                    NOTICE_TEXT.format(mention=message.author.mention),
                    delete_after=8,
                )
            except Exception:
                pass

async def setup(bot: commands.Bot):
    # Ganti GUILD_ID_WHITELIST di atas bila ingin whitelist undangan ke server sendiri
    await bot.add_cog(AntiInvite(bot))
