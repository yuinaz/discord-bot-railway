import re, os, discord, asyncio, pathlib
from discord.ext import commands
from modules.discord_bot.utils.actions import delete_message_safe

from ..helpers.env import (
    NSFW_INVITE_AUTOBAN, LOG_CHANNEL_ID,
    BAN_LOG_CHANNEL_ID, BAN_LOG_CHANNEL_NAME,
)

INVITE_RE = re.compile(r"(?:https?://)?(?:discord(?:app)?\.com/invite/|discord\.gg/|dis\.gd/)([A-Za-z0-9-]+)", re.IGNORECASE)
NSFW_WORDS = {"nsfw","18+","hentai","porn","xxx","sex","lewd","r18","🔞","onlyfans","boobs","nude","nudity","erotic"}
BAN_DELETE_MESSAGE_DAYS = 7
OWN_GUILD_WHITELIST = {int(x) for x in os.getenv('OWN_GUILD_WHITELIST','').split(',') if x.isdigit()}

ASSET_CANDIDATE_DIRS = [
    pathlib.Path("modules/discord_bot/assets"),
    pathlib.Path("modules/assets"),
    pathlib.Path("assets"),
]

def _find_asset(basename: str) -> pathlib.Path | None:
    names = [f"{basename}.png", f"{basename}.webp", f"{basename}.jpg", f"{basename}.jpeg"]
    for d in ASSET_CANDIDATE_DIRS:
        for n in names:
            p = d / n
            if p.exists():
                return p
    return None

def _norm(s: str) -> str:
    # Normalisasi nama channel untuk handle variasi "💬︲ngobrol", "ngobrol", dll
    s = s.casefold()
    for ch in (" ", "︲", "|", "・", "—", "–", "_"):
        s = s.replace(ch, "")
    return s

def _get_ban_log_channel(guild: discord.Guild) -> discord.TextChannel | None:
    # 1) ID khusus ban
    if BAN_LOG_CHANNEL_ID:
        ch = guild.get_channel(BAN_LOG_CHANNEL_ID)
        if isinstance(ch, discord.TextChannel):
            return ch
    # 2) Nama khusus ban (BAN_LOG_CHANNEL_NAME)
    if BAN_LOG_CHANNEL_NAME:
        target = _norm(BAN_LOG_CHANNEL_NAME)
        for ch in guild.text_channels:
            if _norm(ch.name) == target:
                return ch
    # 3) Terakhir: pakai LOG_CHANNEL_ID (biar tetap ada log)
    if LOG_CHANNEL_ID:
        ch = guild.get_channel(LOG_CHANNEL_ID)
        if isinstance(ch, discord.TextChannel):
            return ch
    return None

def _build_ban_embed(message: discord.Message, invite, action: str) -> tuple[discord.Embed, discord.File | None]:
    user = message.author
    g = getattr(invite, "guild", None)
    c = getattr(invite, "channel", None)

    desc = f"**{user.mention}** terdeteksi mengirim undangan **NSFW** dan dikenai **{action}**."
    emb = discord.Embed(title="Autoban NSFW Discord Invite", description=desc, color=discord.Color.red())
    emb.add_field(name="User", value=f"{user} (`{user.id}`)", inline=False)
    if g:
        emb.add_field(name="Invite Guild", value=f"{getattr(g,'name', '-')}", inline=True)
    if c:
        emb.add_field(name="Invite Channel", value=f"{getattr(c,'name','-')}", inline=True)
    emb.add_field(name="Pesan", value=(message.content or "—")[:400], inline=False)

    # FibiLaugh image
    file = None
    fp = _find_asset("fibilaugh")
    if fp:
        file = discord.File(fp, filename=fp.name)
        emb.set_image(url=f"attachment://{fp.name}")
    return emb, file

class AntiInviteAutoban(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not NSFW_INVITE_AUTOBAN: return
        if not message or message.author.bot: return
        m = INVITE_RE.search(message.content or "")
        if not m: return

        code = m.group(1)
        invite = None
        try:
            invite = await self.bot.fetch_invite(code, with_counts=False, with_expiration=False)
        except Exception:
            invite = None

        # whitelist (jika invite ke guild sendiri, dll)
        guild = getattr(invite, "guild", None)
        if guild and getattr(guild, "id", None) in OWN_GUILD_WHITELIST:
            return

        # deteksi nsfw
        is_nsfw = False
        channel = getattr(invite, "channel", None) if invite else None
        try:
            if channel and hasattr(channel, "nsfw") and channel.nsfw: is_nsfw = True
        except Exception: pass
        try:
            nsfw_level = getattr(guild, "nsfw_level", None)
            if nsfw_level is not None:
                val = int(getattr(nsfw_level, "value", nsfw_level))
                if val >= 2: is_nsfw = True
            elif str(nsfw_level).lower() in {"explicit","age_restricted"}: is_nsfw = True
        except Exception: pass
        try:
            texts = []
            if guild: texts += [getattr(guild, "name", "") or "", getattr(guild, "description", "") or ""]
            if channel: texts += [getattr(channel, "name", "") or "", getattr(channel, "topic", "") or ""]
            st = " ".join(texts).lower()
            if any(k in st for k in NSFW_WORDS): is_nsfw = True
        except Exception: pass

        if not is_nsfw: return

        # tindakan
        action_done = "moderation"
        try:
            if message.guild and message.guild.me and message.guild.me.guild_permissions.manage_messages:
                await delete_message_safe(message, actor='anti_invite_autoban')
except Exception: pass
        except Exception: pass

        try:
            if message.guild and message.guild.me and message.guild.me.guild_permissions.ban_members:
                await message.guild.ban(message.author, delete_message_days=BAN_DELETE_MESSAGE_DAYS,
                                        reason="Posting NSFW Discord invite (auto)")
                action_done = "ban"
            elif message.guild and message.guild.me and message.guild.me.guild_permissions.moderate_members:
                duration = discord.utils.utcnow() + discord.timedelta(days=7)
                await message.author.edit(timeout=duration, reason="Posting NSFW Discord invite (auto)")
                action_done = "timeout 7d"
        except Exception:
            pass

        # log ke channel ban (pakai nama/ID sesuai env)
        log_ch = _get_ban_log_channel(message.guild)
        if log_ch:
            try:
                emb, file = _build_ban_embed(message, invite, action_done)
                if file:
                    await log_ch.send(embed=emb, file=file)
                else:
                    await log_ch.send(embed=emb)
            except Exception:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiInviteAutoban(bot))
