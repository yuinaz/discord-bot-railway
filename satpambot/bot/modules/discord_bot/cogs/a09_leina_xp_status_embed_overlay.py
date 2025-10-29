from __future__ import annotations
import os, asyncio, logging, datetime
import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

# Built-in defaults (safe if ENV absent)
DEF_CHAN_ID  = int(os.getenv("LEINA_XP_STATUS_CHANNEL_ID", os.getenv("KV_JSON_CHANNEL_ID","1400375184048787566")))
DEF_MSG_ID   = int(os.getenv("LEINA_XP_STATUS_MESSAGE_ID", os.getenv("KV_JSON_MESSAGE_ID","1432060859252998268")))
DEF_MARKER   = os.getenv("LEINA_XP_STATUS_MARKER", os.getenv("KV_JSON_MARKER","leina:xp_status"))
DEF_PERIOD_S = int(float(os.getenv("LEINA_XP_STATUS_PERIOD_SEC", "1200")))

def _now_ts():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

class LeinaXPStatusEmbedOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.period = max(60, DEF_PERIOD_S)  # guard minimum 60s
        self.chan_id = DEF_CHAN_ID
        self.msg_id = DEF_MSG_ID
        self.marker = DEF_MARKER
        self._task = None

    @commands.Cog.listener()
    async def on_ready(self):
        if not self._task:
            self._task = asyncio.create_task(self._runner(), name="leina_xp_status_runner")
            log.info("[xp-status] started (period=%ss)", self.period)

    async def _runner(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await self._tick_once()
            except Exception as e:
                log.warning("[xp-status] tick failed: %r", e)
            await asyncio.sleep(self.period)

    async def _ensure_message(self, ch: discord.TextChannel) -> discord.Message:
        # Try fetch by ID first
        if self.msg_id:
            try:
                m = await ch.fetch_message(self.msg_id)
                return m
            except Exception:
                pass
        # Try find by marker among pins
        try:
            pins = await ch.pins()
            for m in pins:
                if m.content and (self.marker in m.content):
                    self.msg_id = int(m.id)
                    return m
        except Exception:
            pass
        # Create a new message with marker and pin
        m = await ch.send(self.marker)
        try:
            await m.pin()
        except Exception:
            pass
        self.msg_id = int(m.id)
        return m

    async def _resolve_stage(self):
        """Return (label, percent, cur, req, total) from resolver or KV fallback."""
        # Try xp_total_resolver (it may be overlayed to read KV pinned JSON)
        label, percent, cur, req, total = "KULIAH-S1", 0.0, 0, 19000, 0
        try:
            from satpambot.bot.modules.discord_bot.helpers.xp_total_resolver import stage_preferred, resolve_senior_total
            lbl, pct, meta = await stage_preferred()
            label = str(lbl)
            percent = float(pct)
            cur = int(meta.get("current", 0))
            req = int(meta.get("required", 1))
            total = int(await resolve_senior_total() or 0)
            return label, percent, cur, req, total
        except Exception:
            pass
        # KV fallback (if available)
        try:
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            kv = PinnedJSONKV(self.bot)
            m = await kv.get_map()
            label = str(m.get("xp:stage:label", label))
            percent = float(m.get("xp:stage:percent", percent))
            cur = int(m.get("xp:stage:current", cur))
            req = int(m.get("xp:stage:required", req))
            total = int(m.get(os.getenv("XP_SENIOR_KEY","xp:bot:senior_total"), total))
        except Exception:
            pass
        return label, percent, cur, req, total

    def _build_embed(self, label: str, percent: float, cur: int, req: int, total: int) -> discord.Embed:
        e = discord.Embed(title="Leina Progress", description=f"**{label}** — {percent:.1f}%",
                          colour=0x00B8D9)
        e.add_field(name="Per-Level", value=f"{cur} / {req} XP", inline=True)
        e.add_field(name="Total", value=f"{total} XP", inline=True)
        e.set_footer(text=f"{self.marker} • {_now_ts()}")
        return e

    async def _tick_once(self):
        ch = self.bot.get_channel(self.chan_id)  # type: ignore
        if ch is None:
            ch = await self.bot.fetch_channel(self.chan_id)  # type: ignore
        msg = await self._ensure_message(ch)
        label, percent, cur, req, total = await self._resolve_stage()
        embed = self._build_embed(label, percent, cur, req, total)
        # Update message content (marker) + embed; ensure pinned
        await msg.edit(content=self.marker, embed=embed)
        try:
            await msg.pin()
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(LeinaXPStatusEmbedOverlay(bot))
    log.info("[xp-status] overlay loaded")
