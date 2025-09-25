# rate_limit_guard.py — Global send() backoff for Discord 429/Cloudflare 1015
from __future__ import annotations
import asyncio, time, logging
from collections import defaultdict
from typing import Dict

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

class _PerChannelBucket:
    __slots__ = ("capacity", "refill_rate", "tokens", "last", "lock")
    def __init__(self, capacity: int = 5, refill_rate: float = 1.0):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last = time.monotonic()
        self.lock = asyncio.Lock()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last
        self.last = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)

    async def acquire(self):
        async with self.lock:
            while True:
                self._refill()
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
                needed = 1.0 - self.tokens
                wait = max(0.2, needed / self.refill_rate)
                await asyncio.sleep(wait)

class RateLimitGuard(commands.Cog):
    _orig_send = None
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.buckets: Dict[int, _PerChannelBucket] = defaultdict(lambda: _PerChannelBucket(capacity=5, refill_rate=1.0))

    def _get_bucket(self, channel: discord.abc.Messageable) -> _PerChannelBucket:
        cid = getattr(channel, "id", 0) or 0
        return self.buckets[cid]

    async def _safe_send(self, channel, *args, **kwargs):
        bucket = self._get_bucket(channel)
        await bucket.acquire()

        tries = 0
        while True:
            tries += 1
            try:
                return await self._orig_send(channel, *args, **kwargs)
            except discord.HTTPException as e:
                status = getattr(e, "status", None)
                text = ""
                try:
                    text = await e.response.text() if e.response else ""
                except Exception:
                    pass

                if status == 429 or ("cloudflare" in text.lower() and "error 1015" in text.lower()):
                    retry_after = 0.0
                    try:
                        if e.response:
                            h = e.response.headers
                            ra = h.get("Retry-After") or h.get("retry-after")
                            xra = h.get("X-RateLimit-Reset-After") or h.get("x-ratelimit-reset-after")
                            if ra:
                                retry_after = float(ra)
                            elif xra:
                                retry_after = float(xra)
                    except Exception:
                        pass
                    if retry_after <= 0:
                        retry_after = 30.0 if "1015" in text else 2.5
                    extra = min(30.0, 1.5 ** (tries - 1))
                    wait = min(60.0, retry_after + extra)
                    log.warning("[rate_limit_guard] %s on send; sleeping %.2fs (try %d)", "1015/CF" if "1015" in text else f"HTTP {status}", wait, tries)
                    await asyncio.sleep(wait)
                    await asyncio.sleep(0.1)
                    continue
                else:
                    raise
            except Exception:
                raise

    @commands.Cog.listener()
    async def on_ready(self):
        if RateLimitGuard._orig_send is None:
            RateLimitGuard._orig_send = discord.abc.Messageable.send
            discord.abc.Messageable.send = self._safe_send  # type: ignore
            log.info("[rate_limit_guard] monkeypatched Messageable.send with backoff/limiter")

async def setup(bot: commands.Bot):
    await bot.add_cog(RateLimitGuard(bot))
