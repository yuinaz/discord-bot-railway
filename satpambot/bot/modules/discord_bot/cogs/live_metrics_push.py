from __future__ import annotations
import logging
import math
from discord.ext import commands, tasks
import discord

log = logging.getLogger("satpambot.live_metrics")

try:
    # shared store yang dibaca oleh /api/live/stats
    from satpambot.dashboard.live_store import set_stats
except Exception:
    def set_stats(d):  # fallback aman jika import gagal
        pass

def _safe_latency_ms(bot: commands.Bot) -> int:
    """Konversi bot.latency (detik) -> ms, tahan terhadap inf/NaN/None/negatif."""
    try:
        lat = float(getattr(bot, "latency", 0.0) or 0.0)  # detik (float)
    except Exception:
        lat = 0.0
    if not math.isfinite(lat) or lat < 0.0:
        return 0
    ms = lat * 1000.0
    # clamp ke rentang wajar (mis. 0..600000ms = 10 menit) agar tidak overflow
    if ms < 0 or ms > 600000:
        return 0
    return int(ms)

def snapshot(bot: commands.Bot) -> dict:
    guilds = list(getattr(bot, "guilds", []) or [])
    gcount = len(guilds)

    channels = 0
    threads = 0
    members_total = 0

    for g in guilds:
        try:
            channels += sum(1 for _ in g.channels)
        except Exception:
            pass
        try:
            threads += len(getattr(g, "threads", []) or [])
        except Exception:
            pass
        try:
            members_total += (g.member_count or len(getattr(g, "members", []) or []))
        except Exception:
            pass

    # online (butuh intents.presences True; kalau tidak aktif, hasil bisa 0)
    online = 0
    try:
        off = discord.Status.offline
        for m in bot.get_all_members():
            st = getattr(m, "status", None)
            if st is not None and st != off:
                online += 1
    except Exception:
        online = 0

    latency_ms = _safe_latency_ms(bot)

    return {
        "guilds": gcount,
        "members": int(members_total),
        "online": int(online),
        "channels": int(channels),
        "threads": int(threads),
        "latency_ms": latency_ms,
    }

class LiveMetricsPush(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.push_loop.start()

    def cog_unload(self):
        self.push_loop.cancel()

    @tasks.loop(seconds=2.0)
    async def push_loop(self):
        if not self.bot.is_ready():
            return
        # Lindungi loop dari error sesaat agar tidak mati
        try:
            stats = snapshot(self.bot)
            set_stats(stats)
        except Exception as e:
            log.warning("[live_metrics] push_loop error: %r", e)

    @push_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
        try:
            set_stats(snapshot(self.bot))
        except Exception as e:
            log.debug("[live_metrics] first snapshot error: %r", e)

    # Event untuk update cepat
    @commands.Cog.listener()
    async def on_ready(self):
        try:
            set_stats(snapshot(self.bot))
        except Exception as e:
            log.debug("[live_metrics] on_ready snapshot error: %r", e)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        try: set_stats(snapshot(self.bot))
        except Exception as e: log.debug("[live_metrics] on_guild_join: %r", e)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        try: set_stats(snapshot(self.bot))
        except Exception as e: log.debug("[live_metrics] on_guild_remove: %r", e)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, ch):
        try: set_stats(snapshot(self.bot))
        except Exception as e: log.debug("[live_metrics] on_guild_channel_create: %r", e)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, ch):
        try: set_stats(snapshot(self.bot))
        except Exception as e: log.debug("[live_metrics] on_guild_channel_delete: %r", e)

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        try: set_stats(snapshot(self.bot))
        except Exception as e: log.debug("[live_metrics] on_thread_create: %r", e)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread):
        try: set_stats(snapshot(self.bot))
        except Exception as e: log.debug("[live_metrics] on_thread_delete: %r", e)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        try: set_stats(snapshot(self.bot))
        except Exception as e: log.debug("[live_metrics] on_member_join: %r", e)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        try: set_stats(snapshot(self.bot))
        except Exception as e: log.debug("[live_metrics] on_member_remove: %r", e)

    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        try: set_stats(snapshot(self.bot))
        except Exception as e: log.debug("[live_metrics] on_presence_update: %r", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(LiveMetricsPush(bot))
