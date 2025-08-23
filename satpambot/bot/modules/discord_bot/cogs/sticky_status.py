
import os, asyncio, logging, time
from typing import Optional, Tuple
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

STICKY_CHANNEL_ID_DEFAULT = int(os.environ.get("STICKY_CHANNEL_ID", "1400375184048787566"))
STICKY_REFRESH_SEC = int(os.environ.get("STICKY_REFRESH_SEC", "300"))  # 5 menit
STICKY_TAG = os.environ.get("STICKY_TAG", "SATPAMBOT_STATUS_V1")
TZ = timezone(timedelta(hours=7))  # WIB

_STORE_PATH = os.environ.get("SATPAMBOT_STICKY_FILE",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "sticky_state.json"))

def _read_saved_id() -> Optional[int]:
    try:
        import json
        with open(_STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return int(data.get("message_id")) if data.get("message_id") else None
    except Exception:
        return None

def _write_saved_id(mid: int) -> None:
    try:
        import json
        tmp = _STORE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"message_id": int(mid)}, f)
        os.replace(tmp, _STORE_PATH)
    except Exception as e:
        log.debug("failed saving sticky id: %s", e)

def _format_uptime(start_ts: float) -> str:
    delta = int(time.time() - start_ts)
    m, s = divmod(delta, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    if d: return f"{d}d {h}h {m}m"
    if h: return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"

class StickyStatus(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_ts = time.time()
        self._lock = asyncio.Lock()
        self.refresh.change_interval(seconds=STICKY_REFRESH_SEC)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.refresh.is_running():
            log.info("[sticky_status] loop %ss on channel %s", STICKY_REFRESH_SEC, STICKY_CHANNEL_ID_DEFAULT)
            self.refresh.start()

    def _build(self) -> Tuple[str, discord.Embed]:
        user = f"{self.bot.user.name}#{self.bot.user.discriminator}" if self.bot.user else "bot"
        pres = "online" if str(getattr(self.bot, "status", "online")) == "online" else "offline"
        uptime = _format_uptime(self.start_ts)
        header = f"✅ Online sebagai {user} | presence={pres} | uptime={uptime}"
        emb = discord.Embed(title="SatpamBot Status", description="Status ringkas bot.", color=0x00d26a)
        emb.add_field(name="Akun", value=user, inline=False)
        emb.add_field(name="Presence", value=f"**{pres}**", inline=True)
        emb.add_field(name="Uptime", value=uptime, inline=True)
        now = datetime.now(TZ).strftime("Today at %I:%M %p")
        emb.set_footer(text=f"{STICKY_TAG} • WIB (UTC+7) • {now}")
        return header, emb

    async def _get_or_create(self, ch: discord.TextChannel) -> discord.Message:
        saved = _read_saved_id()
        if saved:
            try:
                return await ch.fetch_message(saved)
            except Exception:
                pass

        candidate = None
        async for m in ch.history(limit=30):
            if m.author == self.bot.user:
                tag_ok = False
                if m.embeds:
                    foot = (m.embeds[0].footer.text or "") if m.embeds[0].footer else ""
                    tag_ok = STICKY_TAG in foot
                if tag_ok:
                    if candidate is None:
                        candidate = m
                    else:
                        try: await m.delete()
                        except Exception: pass

        if candidate:
            _write_saved_id(candidate.id)
            return candidate

        content, embed = self._build()
        msg = await ch.send(content=content, embed=embed, silent=True)
        _write_saved_id(msg.id)
        return msg

    @tasks.loop(seconds=300.0)
    async def refresh(self):
        async with self._lock:
            try:
                ch = self.bot.get_channel(STICKY_CHANNEL_ID_DEFAULT)
                if not isinstance(ch, discord.TextChannel):
                    log.warning("[sticky_status] channel %s not found", STICKY_CHANNEL_ID_DEFAULT)
                    return
                msg = await self._get_or_create(ch)
                content, embed = self._build()
                need_edit = True
                if msg.content == content and msg.embeds:
                    e = msg.embeds[0]
                    try:
                        if e.title == embed.title and e.fields == embed.fields:
                            need_edit = False
                    except Exception:
                        need_edit = True
                if need_edit:
                    await msg.edit(content=content, embed=embed)
            except discord.HTTPException as e:
                log.debug("[sticky_status] edit skipped: %s", e)
            except Exception as e:
                log.warning("[sticky_status] loop error: %s", e)

    @refresh.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(StickyStatus(bot))
