
from __future__ import annotations
import logging, asyncio
from discord.ext import commands

log = logging.getLogger(__name__)

def _to_int(v, d=0):
    try: return int(v)
    except Exception:
        try: return int(float(v))
        except Exception: return d

class LeinaXPStatusEmbedOverlay(commands.Cog):
    """Render 'Leina Progress' strictly from pinned xp:stage:*; total from Upstash.
    Never reads learning:status_json to avoid SMP-L* contamination.
    """
    def __init__(self, bot):
        self.bot = bot
        from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_int
        self.interval = cfg_int("LEINA_XP_STATUS_INTERVAL", 120)
        self._task = None

    async def _fetch_state(self):
        from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
        from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_str
        kv = PinnedJSONKV(self.bot)
        m = await kv.get_map()

        label = str(m.get("xp:stage:label") or "")
        cur   = _to_int(m.get("xp:stage:current", 0), 0)
        req   = _to_int(m.get("xp:stage:required", 1), 1)
        pct   = float(m.get("xp:stage:percent", 0) or 0.0)

        # total from Upstash (fallback to pinned copy if any)
        total_key = cfg_str("XP_SENIOR_KEY","xp:bot:senior_total")
        total = 0
        try:
            from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
            us = UpstashClient()
            raw = await us.cmd("GET", total_key)
            total = _to_int(raw, _to_int(m.get(total_key, 0), 0))
        except Exception:
            total = _to_int(m.get(total_key, 0), 0)

        return label, cur, req, pct, total

    async def _render_once(self):
        try:
            label, cur, req, pct, total = await self._fetch_state()
            if not label.startswith(("KULIAH-","MAGANG")):
                # do not publish misleading embed
                log.info("[leina:xp_status] pinned stage not ready; skip")
                return

            # Build a simple embed via helper if available; else log only
            try:
                from satpambot.bot.modules.discord_bot.helpers.embed_scribe import upsert_embed
                fields = [
                    ("Per‑Level", f"{cur:,} / {req:,} XP", True),
                    ("Total",     f"{total:,} XP", True),
                ]
                title = "Leina Progress"
                desc = f"{label} — {pct:.1f}%"
                await upsert_embed(self.bot, "leina:xp_status", title=title, description=desc, fields=fields)
            except Exception as e:
                log.info("[leina:xp_status] %s — %.1f%%  (%s/%s) total=%s  (embed_scribe err=%r)",
                         label, pct, cur, req, total, e)
        except Exception as e:
            log.debug("[leina:xp_status] render failed: %r", e)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        while True:
            await self._render_once()
            await asyncio.sleep(self.interval)

async def setup(bot):
    await bot.add_cog(LeinaXPStatusEmbedOverlay(bot))
