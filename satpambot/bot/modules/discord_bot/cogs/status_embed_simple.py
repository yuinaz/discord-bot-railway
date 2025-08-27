from __future__ import annotations
import asyncio, os, datetime as dt
try:
    import zoneinfo
except Exception:
    zoneinfo = None
import discord
from discord.ext import commands, tasks

MARKER = "SATPAMBOT_STATUS_V1"
TZ = os.getenv("TZ") or os.getenv("TIMEZONE") or "Asia/Jakarta"
if zoneinfo:
    try:
        ZONE = zoneinfo.ZoneInfo(TZ)
    except Exception:
        ZONE = zoneinfo.ZoneInfo("Asia/Jakarta")
else:
    ZONE = None

def _fmt_wib(now=None):
    if ZONE:
        now = now or dt.datetime.now(tz=ZONE)
    else:
        now = dt.datetime.utcnow()
    return now.strftime("%A %d %b %Y %H:%M") + " WIB"

def _uptime(delta: dt.timedelta) -> str:
    s = int(delta.total_seconds())
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h: return f"{h}h {m}m"
    if m: return f"{m}m {s}s"
    return f"{s}s"

def _build_embed(bot: commands.Bot, started_at: dt.datetime) -> discord.Embed:
    e = discord.Embed(title="SatpamBot Status", description="Status ringkas bot.", color=0x2ecc71)
    e.add_field(name="Akun", value=str(bot.user), inline=False)
    e.add_field(name="Presence", value=f"presence={str(bot.status).split('.')[-1]}", inline=True)
    e.add_field(name="Uptime", value=_uptime(dt.datetime.now(tz=dt.timezone.utc) - started_at), inline=True)
    e.set_footer(text=f"{MARKER} • {_fmt_wib()}")
    return e

class StatusEmbedSimple(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_id = int(os.getenv("STICKY_CHANNEL_ID") or os.getenv("LOG_CHANNEL_ID") or os.getenv("LOG_CHANNEL_ID_RAW") or 0)
        self.message_id: int | None = None
        self.started_at = dt.datetime.now(tz=dt.timezone.utc)
        self._task.start()

    async def _resolve_channel(self) -> discord.TextChannel | None:
        if not self.channel_id:
            return None
        ch = self.bot.get_channel(self.channel_id)
        if isinstance(ch, discord.TextChannel):
            return ch
        try:
            ch = await self.bot.fetch_channel(self.channel_id)
            if isinstance(ch, discord.TextChannel): return ch
        except Exception:
            return None
        return None

    async def _find_existing(self, ch: discord.TextChannel) -> discord.Message | None:
        pins = await ch.pins()
        for m in pins:
            if m.author.id == self.bot.user.id and m.embeds:
                try:
                    if MARKER in (m.embeds[0].footer.text or ""):
                        return m
                except Exception:
                    pass
        async for m in ch.history(limit=30):
            if m.author.id == self.bot.user.id and m.embeds:
                try:
                    if MARKER in (m.embeds[0].footer.text or ""):
                        return m
                except Exception:
                    pass
        return None

    @tasks.loop(seconds=60)
    async def _task(self):
        try:
            ch = await self._resolve_channel()
            if not ch: return
            msg = None
            if self.message_id:
                try:
                    msg = await ch.fetch_message(self.message_id)
                except Exception:
                    msg = None
            if not msg:
                msg = await self._find_existing(ch)
                if msg:
                    self.message_id = msg.id
            e = _build_embed(self.bot, self.started_at)
            content = f"✅ Online sebagai {self.bot.user} | presence={str(self.bot.status).split('.')[-1]} | uptime={_uptime(dt.datetime.now(tz=dt.timezone.utc)-self.started_at)}"
            if msg:
                await msg.edit(embed=e, content=content, allowed_mentions=discord.AllowedMentions.none())
            else:
                msg = await ch.send(content=content, embed=e, allowed_mentions=discord.AllowedMentions.none())
                self.message_id = msg.id
                try:
                    await msg.pin()
                except Exception:
                    pass
        except Exception:
            pass

    @_task.before_loop
    async def _ready(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(StatusEmbedSimple(bot))
