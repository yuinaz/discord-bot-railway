from __future__ import annotations
import discord
from discord.ext import commands, tasks

try:
    from satpambot.dashboard.live_store import set_stats
except Exception:
    def set_stats(d): pass  # fallback aman

def snapshot(bot: commands.Bot) -> dict:
    guilds = list(getattr(bot, "guilds", []) or [])
    gcount = len(guilds)
    channels = 0
    threads = 0
    members_total = 0

    for g in guilds:
        try: channels += sum(1 for _ in g.channels)
        except Exception: pass
        try: threads += len(getattr(g, "threads", []) or [])
        except Exception: pass
        # cepat & akurat: pakai server-provided count
        try: members_total += (g.member_count or len(getattr(g, "members", []) or []))
        except Exception: pass

    online = 0
    try:
        off = discord.Status.offline
        for m in bot.get_all_members():
            st = getattr(m, "status", None)
            if st is not None and st != off:
                online += 1
    except Exception:
        online = 0  # jika presence intent off

    latency_ms = int(float(getattr(bot, "latency", 0.0) or 0.0) * 1000)
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
        set_stats(snapshot(self.bot))

    @push_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
        set_stats(snapshot(self.bot))

    # event hooks untuk refresh cepat
    @commands.Cog.listener()
    async def on_ready(self):
        set_stats(snapshot(self.bot))
    @commands.Cog.listener()
    async def on_guild_join(self, guild): set_stats(snapshot(self.bot))
    @commands.Cog.listener()
    async def on_guild_remove(self, guild): set_stats(snapshot(self.bot))
    @commands.Cog.listener()
    async def on_guild_channel_create(self, ch): set_stats(snapshot(self.bot))
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, ch): set_stats(snapshot(self.bot))
    @commands.Cog.listener()
    async def on_thread_create(self, thread): set_stats(snapshot(self.bot))
    @commands.Cog.listener()
    async def on_thread_delete(self, thread): set_stats(snapshot(self.bot))
    @commands.Cog.listener()
    async def on_member_join(self, member): set_stats(snapshot(self.bot))
    @commands.Cog.listener()
    async def on_member_remove(self, member): set_stats(snapshot(self.bot))
    @commands.Cog.listener()
    async def on_presence_update(self, before, after): set_stats(snapshot(self.bot))

async def setup(bot: commands.Bot):
    await bot.add_cog(LiveMetricsPush(bot))
