
# -*- coding: utf-8 -*-
from __future__ import annotations
import time, math, asyncio
from typing import Dict, Tuple
import discord
from discord.ext import commands, tasks

def _lat_ms(bot)->int:
    try:
        v = float(getattr(bot,'latency',0.0) or 0.0)
        if not math.isfinite(v) or v<0: return 0
        return int(v*1000.0)
    except Exception:
        return 0

async def _rest_counts(bot)->Tuple[int,int]:
    mem=onl=0
    for g in list(bot.guilds):
        try:
            fg = await bot.fetch_guild(g.id, with_counts=True)
            mem += int(getattr(fg,"approximate_member_count",0) or 0)
            onl += int(getattr(fg,"approximate_presence_count",0) or 0)
        except Exception: pass
        await asyncio.sleep(0)
    return mem,onl

def _cache_counts(bot)->Tuple[int,int]:
    mem=onl=0
    for g in list(bot.guilds):
        mc = getattr(g,"member_count",None)
        if isinstance(mc,int): mem += max(0,mc)
        try:
            onl += sum(1 for m in g.members if getattr(m,"status",discord.Status.offline)!=discord.Status.offline)
        except Exception: pass
    return mem,onl

async def snapshot(bot)->Dict[str,int]:
    guilds = len(bot.guilds)
    try: channels=sum(len(g.channels) for g in bot.guilds)
    except Exception: channels=0
    try: threads=sum(len(getattr(g,"threads",[])) for g in bot.guilds)
    except Exception: threads=0

    mem,onl = _cache_counts(bot)
    if mem==0 or onl==0:
        rmem,ronl = await _rest_counts(bot)
        mem=max(mem,rmem); onl=max(onl,ronl)

    return {"guilds":guilds,"members":mem,"online":onl,"channels":channels,"threads":threads,"latency_ms":_lat_ms(bot),"updated":int(time.time())}

class LiveMetricsPush(commands.Cog):
    def __init__(self, bot:commands.Bot)->None:
        self.bot=bot
        self._last_rest=0.0
        self._loop.start()

    @tasks.loop(seconds=5.0)
    async def _loop(self)->None:
        try:
            snap = await snapshot(self.bot)
            # find setter
            app = getattr(self.bot,"_flask_app",None)
            set_fn = None
            if app and hasattr(app.config,"get"):
                set_fn = app.config.get("set_stats_fn")
            if not set_fn:
                # fallback import
                try:
                    from satpambot.dashboard.live_store import set_stats as set_fn  # type: ignore
                except Exception:
                    set_fn=None
            if set_fn: set_fn(snap)
        except Exception as e:
            print("[live_metrics] WARN:", repr(e))

    @_loop.before_loop
    async def _before(self)->None:
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot)->None:
    await bot.add_cog(LiveMetricsPush(bot))
