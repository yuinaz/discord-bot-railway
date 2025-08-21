# patched status sticky (WIB + hourly edit + anti-duplicate)
import os, time, contextlib, logging, discord
from discord.ext import commands, tasks
from datetime import datetime
from pathlib import Path
try:
    from zoneinfo import ZoneInfo
    WIB = ZoneInfo("Asia/Jakarta")
except Exception:
    WIB = None

log = logging.getLogger(__name__)
_STATUS_MARKER = "SATPAMBOT_STATUS_V1"
MIN_INTERVAL = 3600  # 1 hour hardcoded
STATUS_ID_PATH = Path("data") / "status_msg_id.txt"
STATUS_ID_PATH.parent.mkdir(parents=True, exist_ok=True)

def _fmt_wib(ts: float) -> str:
    try:
        if WIB:
            return datetime.fromtimestamp(ts, WIB).strftime("%Y-%m-%d %H:%M WIB")
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return "—"

async def _find_status_message(ch):
    try:
        if STATUS_ID_PATH.exists():
            mid = int(STATUS_ID_PATH.read_text().strip())
            m = await ch.fetch_message(mid)
            if m and m.author == ch.guild.me:
                text = (m.content or "") + "".join(e.footer.text or "" for e in m.embeds)
                if _STATUS_MARKER in text:
                    return m
    except Exception:
        pass
    try:
        async for m in ch.history(limit=50):
            if m.author == ch.guild.me:
                text = (m.content or "") + "".join(e.footer.text or "" for e in m.embeds)
                if _STATUS_MARKER in text:
                    return m
    except Exception as e:
        log.warning("[status] history scan failed: %s", e)
    return None

async def _post_or_edit_status(bot, ch):
    now = time.time()
    footer = f"{_STATUS_MARKER} • {_fmt_wib(now)}"
    emb = discord.Embed(title="SatpamBot Status", description="Status ringkas bot.", color=0x57f287)
    emb.add_field(name="Akun", value=str(bot.user), inline=False)
    emb.add_field(name="Presence", value="`presence=online`", inline=True)
    up = int(now - (getattr(bot, 'start_time', now)))
    m, s = divmod(up, 60); h, m = divmod(m, 60)
    emb.add_field(name="Uptime", value=f"{h}h {m}m {s}s", inline=True)
    emb.set_footer(text=footer)

    old = await _find_status_message(ch)
    content = f"✅ Online sebagai **{bot.user}** | `presence=online` | `uptime={h}h {m}m {s}s`"
    if old:
        try:
            await old.edit(content=content, embed=emb)
            return old
        except Exception as e:
            log.warning("[status] edit failed: %s (will create new)", e)

    newm = await ch.send(content=content, embed=emb)
    try: STATUS_ID_PATH.write_text(str(newm.id))
    except Exception: pass
    # cleanup dups
    try:
        async for m in ch.history(limit=30):
            if m.id == newm.id: continue
            if m.author == bot.user:
                text = (m.content or "") + "".join(e.footer.text or "" for e in m.embeds)
                if _STATUS_MARKER in text:
                    await m.delete()
    except Exception: pass
    return newm

class StatusStickyPatched(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last = 0.0
        self.task = self._loop.start()

    @tasks.loop(seconds=30)
    async def _loop(self):
        try:
            import discord
            if time.time() - self._last < MIN_INTERVAL: return
            self._last = time.time()
            ch = None
            ch_id = int(os.getenv("LOG_CHANNEL_ID", "0") or "0")
            if ch_id: ch = self.bot.get_channel(ch_id)
            if not ch:
                name = os.getenv("LOG_CHANNEL_NAME", "log-botphising")
                for g in self.bot.guilds:
                    _c = discord.utils.get(g.text_channels, name=name)
                    if _c: ch=_c; break
            
if not ch:
    # Try LOG_CHANNEL_ID as fallback
    _log_id = os.getenv("LOG_CHANNEL_ID")
    if _log_id:
        try:
            _log_id_int = int(_log_id)
            ch = self.bot.get_channel(_log_id_int)
        except Exception:
            ch = None
if not ch:
    # Try common names
    names = [os.getenv("LOG_CHANNEL_NAME", "log-botphising"), "bot-log", "log", "logs"]
    for g in self.bot.guilds:
        for nm in names:
            _c = discord.utils.get(g.text_channels, name=nm)
            if _c:
                ch = _c
                break
        if ch: break
if not ch:
    # Last resort: first text channel we can send to
    for g in self.bot.guilds:
        for _c in g.text_channels:
            p = _c.permissions_for(g.me)
            if p.send_messages and p.embed_links:
                ch = _c; break
        if ch: break
if not ch:
    log.warning("[status] channel not found (tried STATUS_CHANNEL_ID, LOG_CHANNEL_ID, names)")
    return
await _post_or_edit_status(self.bot, ch)
except Exception as e:
            log.exception("[status] update failed: %s", e)

async def setup(bot):
    await bot.add_cog(StatusStickyPatched(bot))
