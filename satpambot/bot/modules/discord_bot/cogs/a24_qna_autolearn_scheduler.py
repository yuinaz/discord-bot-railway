from __future__ import annotations
import asyncio, logging, random, json, hashlib, time
from typing import List
import discord
from discord.ext import commands, tasks
log = logging.getLogger(__name__)

def _cfg_int(k, d=0):
    try:
        from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_int
        return int(cfg_int(k, d))
    except Exception:
        return int(d)

def _cfg_str(k, d=""):
    try:
        from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_str
        return str(cfg_str(k, d))
    except Exception:
        return str(d)

def _flatten_topics(data) -> List[str]:
    items: List[str] = []
    try:
        for _, arr in (data or {}).items():
            for x in arr:
                if isinstance(x, str) and x.strip():
                    items.append(x.strip())
    except Exception:
        pass
    return items

def _sha1(s: str) -> str:
    import hashlib as _h
    return _h.sha1(s.encode("utf-8")).hexdigest()

class _US:
    def __init__(self, bot):
        self.bot = bot
        try:
            from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient  # type: ignore
            self.client = UpstashClient()
        except Exception:
            self.client = None

    async def get(self, key: str):
        if not self.client or not getattr(self.client, "enabled", False):
            return None
        try:
            return await self.client.get_raw(key)
        except Exception:
            return None

    async def setex(self, key: str, val: str, ttl: int = 3600):
        if not self.client or not getattr(self.client, "enabled", False):
            return False
        try:
            return await self.client.setex(key, val, ttl)
        except Exception:
            return False

WAIT_KEY = "qna:waiting"   # released by award overlay
USED_PREFIX = "qna:used:"   # qna:used:<sha1> -> 1 (ttl 1d)

class QnAAutoLearnScheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.interval_sec = max(30, _cfg_int("QNA_INTERVAL_SEC", 60))
        self.enabled = _cfg_int("QNA_ENABLE", 0) == 1
        self._last_post = 0.0
        self.us = _US(bot)
        if self.enabled:
            self.loop.start()
            log.info("[qna-scheduler] enabled every %ss", self.interval_sec)
        else:
            log.info("[qna-scheduler] disabled")

    def cog_unload(self):
        try: self.loop.cancel()
        except Exception: pass

    def _load_topics(self) -> List[str]:
        # Path-based loader for data/config/qna_topics.json
        import os
        data = {}
        try:
            base = os.path.join(os.getcwd(), "data", "config", "qna_topics.json")
            if os.path.exists(base):
                with open(base, "r", encoding="utf-8") as f:
                    data = json.load(f)
        except Exception as e:
            log.warning("[qna-scheduler] topics load fail: %r", e)
        items = _flatten_topics(data)
        if not items:
            items = ["Apa itu SatpamBot?"]
        random.shuffle(items)
        return items

    async def _pick_new_topic(self) -> str:
        topics = self._load_topics()
        for t in topics:
            key = USED_PREFIX + _sha1(t.lower().strip())
            if not await self.us.get(key):
                await self.us.setex(key, "1", ttl=24*3600)
                return t
        # if all used, rotate random
        t = random.choice(topics)
        await self.us.setex(USED_PREFIX + _sha1(t.lower().strip()), "1", ttl=24*3600)
        return t

    @tasks.loop(seconds=5.0)
    async def loop(self):
        if not self.enabled: return
        now = time.time()
        if now - self._last_post < self.interval_sec: return
        try:
            if await self.us.get(WAIT_KEY): return
        except Exception:
            pass

        ch_id = int(_cfg_str("QNA_CHANNEL_ID","0") or "0")
        ch = self.bot.get_channel(ch_id) if ch_id > 0 else None
        if not ch: return

        topic = await self._pick_new_topic()
        emb = discord.Embed(title="QnA Prompt", description=topic)
        await ch.send(embed=emb)
        await self.us.setex(WAIT_KEY, "1", ttl=max(120, self.interval_sec))
        self._last_post = now

async def setup(bot):
    await bot.add_cog(QnAAutoLearnScheduler(bot))
