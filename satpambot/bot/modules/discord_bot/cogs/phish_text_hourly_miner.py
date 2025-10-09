# -*- coding: utf-8 -*-
from __future__ import annotations
import re, asyncio, logging, collections, urllib.parse
import discord
from discord.ext import commands, tasks

from satpambot.bot.modules.discord_bot.helpers.memory_upsert import upsert_pinned_memory
from satpambot.bot.modules.discord_bot.config.self_learning_cfg import (
    LOG_CHANNEL_ID, PHISH_CHANNEL_IDS, PHISH_SCAN_LIMIT,
    PHISH_FIRST_DELAY_SECONDS, PHISH_INTERVAL_SECONDS
)

log = logging.getLogger(__name__)

URL_RE = re.compile(r'https?://[^\s)>\]]+')
BAIT_TERMS = ('nitro','gift','free','gratis','hadiah','airdrop','mint','verify','verifikasi','klik','click','claim','klaim','event','promo','giveaway','hadiah','robux','diamond','mobile legends','mlbb')

def _domain(url: str) -> str:
    try:
        d = urllib.parse.urlparse(url).netloc.lower()
        return d.split(':',1)[0]
    except Exception:
        return ''

class PhishTextHourlyMiner(commands.Cog):
    def __init__(self, bot): 
        self.bot=bot
        self.task=None

    async def cog_load(self):
        self.task=self.loop_collect.start()

    def cog_unload(self):
        if self.task: self.task.cancel()

    @tasks.loop(seconds=PHISH_INTERVAL_SECONDS)
    async def loop_collect(self):
        await self.bot.wait_until_ready()
        targets=set()
        if LOG_CHANNEL_ID:
            ch=self.bot.get_channel(LOG_CHANNEL_ID)
            if isinstance(ch, discord.TextChannel): targets.add(ch)
            for th in getattr(ch, 'threads', []):
                if isinstance(th, discord.Thread) and 'phish' in th.name.lower():
                    targets.add(th)
        for i in PHISH_CHANNEL_IDS:
            ch=self.bot.get_channel(i)
            if isinstance(ch,(discord.TextChannel,discord.Thread)):
                targets.add(ch)

        if not targets:
            log.info("[phish_hourly] no targets")
            return

        domains=collections.Counter()
        baits=collections.Counter()
        for ch in targets:
            try:
                async for m in ch.history(limit=PHISH_SCAN_LIMIT, oldest_first=False):
                    text = (m.content or "").lower()
                    for u in URL_RE.findall(text):
                        d = _domain(u)
                        if d: domains.update([d])
                    for t in BAIT_TERMS:
                        if t in text:
                            baits.update([t])
            except Exception as e:
                log.warning("[phish_hourly] scan fail on %s: %s", getattr(ch,'name',ch.id), e)

        intel = {
            "domains_top": [[k,int(v)] for k,v in domains.most_common(50)],
            "bait_terms_top": [[k,int(v)] for k,v in baits.most_common(50)],
            "scan_limit_per_channel": PHISH_SCAN_LIMIT,
        }
        ok = await upsert_pinned_memory(self.bot, {"threat_intel": intel})
        log.info("[phish_hourly] memory updated: %s", ok)

    @loop_collect.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(PHISH_FIRST_DELAY_SECONDS)
        log.info("[phish_hourly] started (delay=%ss, every=%ss, limit=%s)",
                 PHISH_FIRST_DELAY_SECONDS, PHISH_INTERVAL_SECONDS, PHISH_SCAN_LIMIT)

async def setup(bot):
    await bot.add_cog(PhishTextHourlyMiner(bot))
