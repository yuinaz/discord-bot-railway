# -*- coding: utf-8 -*-
"""
a02_status_pin_embed_overlay (v2)
---------------------------------
- Collapse spam to a single pinned embed in STATUS_CHANNEL_ID by editing it.
- Intercepts both channel.send() and Message.reply() paths.
- Rate-limit edits; if called too fast, queue one delayed edit (coalesce).

ENV:
  STATUS_CHANNEL_ID=1400375184048787566
  STATUS_UPDATE_MIN_SEC=10
  KV_BACKEND=upstash_rest
  UPSTASH_REDIS_REST_URL=...
  UPSTASH_REDIS_REST_TOKEN=...
"""
import os, time, logging, asyncio
from typing import Optional
from discord.ext import commands

log = logging.getLogger(__name__)

class _Upstash:
    def __init__(self):
        self.base = (os.getenv("UPSTASH_REDIS_REST_URL","")).rstrip("/")
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN","")
        self.enabled = bool(self.base and self.token and os.getenv("KV_BACKEND","upstash_rest")=="upstash_rest")
        try:
            import aiohttp
            self._aiohttp = aiohttp
        except Exception as e:
            self._aiohttp = None
            log.warning("[status-pin] aiohttp not available: %r", e)

    async def get(self, key: str) -> Optional[str]:
        if not (self.enabled and self._aiohttp): return None
        url = f"{self.base}/get/{key}"
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            async with self._aiohttp.ClientSession() as s:
                async with s.get(url, headers=headers, timeout=8) as r:
                    data = await r.json(content_type=None)
                    return data.get("result")
        except Exception as e:
            log.warning("[status-pin] Upstash GET %s failed: %r", key, e)
            return None

    async def set(self, key: str, value: str) -> bool:
        if not (self.enabled and self._aiohttp): return False
        url = f"{self.base}/set/{key}/{value}"
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            async with self._aiohttp.ClientSession() as s:
                async with s.post(url, headers=headers, timeout=8) as r:
                    data = await r.json(content_type=None)
                    return data.get("result") == "OK"
        except Exception as e:
            log.warning("[status-pin] Upstash SET %s failed: %r", key, e)
            return False

class StatusPinOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.us = _Upstash()
        self.channel_id = int(os.getenv("STATUS_CHANNEL_ID","1400375184048787566"))
        self.min_sec = int(os.getenv("STATUS_UPDATE_MIN_SEC","10"))
        self._patched = False
        self._queue_text = None
        self._queue_task = None

    # ---- Core helpers ----
    async def _get_msg_id(self) -> Optional[int]:
        v = await self.us.get(f"status_pin:{self.channel_id}:message_id")
        try: return int(v) if v else None
        except Exception: return None

    async def _set_msg_id(self, mid: Optional[int]):
        if mid:
            await self.us.set(f"status_pin:{self.channel_id}:message_id", str(mid))
        else:
            await self.us.set(f"status_pin:{self.channel_id}:message_id", "")

    async def _get_last_ts(self) -> float:
        v = await self.us.get(f"status_pin:{self.channel_id}:ts") or "0"
        try: return float(v)
        except Exception: return 0.0

    async def _set_last_ts(self, ts: float):
        await self.us.set(f"status_pin:{self.channel_id}:ts", str(ts))

    async def _ensure_embed(self, force_text: Optional[str]=None):
        ch = self.bot.get_channel(self.channel_id) or await self.bot.fetch_channel(self.channel_id)
        if ch is None:
            return None
        mid = await self._get_msg_id()
        msg = None
        if mid:
            try:
                msg = await ch.fetch_message(mid)
            except Exception:
                msg = None
        if msg is None:
            # create new pinned message with basic embed
            try:
                import discord
                emb = discord.Embed(title="Leina Status", description=force_text or "Inisialisasi status…")
                m = await ch.send(embed=emb)
                try:
                    await m.pin()
                except Exception:
                    pass
                await self._set_msg_id(m.id)
                return m
            except Exception as e:
                log.warning("[status-pin] cannot create message: %r", e)
                return None
        return msg

    def _normalize_text(self, args, kwargs) -> str:
        # derive a concise text from content/embed(s)
        content = kwargs.get("content")
        if content is None and args and isinstance(args[0], str):
            content = args[0]
        text = ""
        if isinstance(content, str) and content.strip():
            text = content.strip()
        elif "embeds" in kwargs and kwargs["embeds"]:
            try:
                emb = kwargs["embeds"][0]
                text = (getattr(emb, "title", "") or "") + "\n" + (getattr(emb, "description", "") or "")
            except Exception:
                text = "[update]"
        elif "embed" in kwargs and kwargs["embed"] is not None:
            try:
                emb = kwargs["embed"]
                text = (getattr(emb, "title", "") or "") + "\n" + (getattr(emb, "description", "") or "")
            except Exception:
                text = "[update]"
        else:
            text = "[update]"
        # compress multi-lines a bit
        text = "\n".join([ln.rstrip() for ln in (text or "").splitlines() if ln.strip()])[:1800]
        return text or "[update]"

    async def _edit_embed(self, new_text: str, force=False):
        # rate limit & coalesce
        last = await self._get_last_ts()
        now = time.time()
        if not force and now - last < self.min_sec:
            # schedule one delayed update (coalesce)
            self._queue_text = new_text
            if self._queue_task is None or self._queue_task.done():
                async def _later():
                    await asyncio.sleep(max(0.5, self.min_sec - (now - last)))
                    txt = self._queue_text
                    self._queue_text = None
                    await self._edit_embed(txt, force=True)
                self._queue_task = asyncio.create_task(_later())
            return True

        msg = await self._ensure_embed()
        if msg is None: 
            return False
        try:
            import discord
            emb = msg.embeds[0] if msg.embeds else discord.Embed(title="Leina Status")
            emb.description = new_text
            await msg.edit(embed=emb)
            await self._set_last_ts(time.time())
            return True
        except Exception as e:
            log.warning("[status-pin] edit failed: %r", e)
            return False

    # ---- Monkeypatch send() and reply() to collapse spam in STATUS_CHANNEL_ID ----
    def _install_patch(self):
        if self._patched: return
        try:
            import discord.abc as _abc
            _orig_send = _abc.Messageable.send
        except Exception as e:
            log.warning("[status-pin] cannot locate Messageable.send: %r", e)
            return
        overlay = self

        async def _wrapped_send(self, *args, **kwargs):
            try:
                ch_id = getattr(self, "id", None) or getattr(getattr(self, "channel", None), "id", None)
            except Exception:
                ch_id = None
            if ch_id == overlay.channel_id:
                text = overlay._normalize_text(args, kwargs)
                ok = await overlay._edit_embed(text)
                if ok:
                    class _Dummy: id=None
                    return _Dummy()
            return await _orig_send(self, *args, **kwargs)

        _abc.Messageable.send = _wrapped_send

        # Also patch Message.reply, because some code uses reply()
        try:
            import discord
            _orig_reply = discord.Message.reply
            async def _wrapped_reply(msg, *args, **kwargs):
                ch_id = getattr(getattr(msg, "channel", None), "id", None)
                if ch_id == overlay.channel_id:
                    text = overlay._normalize_text(args, kwargs)
                    ok = await overlay._edit_embed(text)
                    if ok:
                        class _Dummy: id=None
                        return _Dummy()
                return await _orig_reply(msg, *args, **kwargs)
            discord.Message.reply = _wrapped_reply
        except Exception as e:
            log.warning("[status-pin] cannot patch Message.reply: %r", e)

        self._patched = True
        log.info("[status-pin] send()/reply() patch installed for channel %s", self.channel_id)

    # ---- Commands ----
    @commands.group(name="status", invoke_without_command=True)
    async def status_group(self, ctx):
        mid = await self._get_msg_id()
        last = await self._get_last_ts()
        await ctx.reply(f"📌 status pin: channel={self.channel_id}, message_id={mid}, rate≥{self.min_sec}s, last={last:.0f}", mention_author=False)

    @status_group.command(name="pin")
    async def status_pin(self, ctx):
        m = await self._ensure_embed("Status aktif.")
        if m: await ctx.reply(f"📌 pinned message id={m.id}", mention_author=False)
        else: await ctx.reply("❌ gagal membuat/pin status.", mention_author=False)

    @status_group.command(name="set")
    async def status_set(self, ctx, *, text: str):
        ok = await self._edit_embed(text, force=True)
        await ctx.reply("✅ updated" if ok else "❌ gagal update", mention_author=False)

    @status_group.command(name="unpin")
    async def status_unpin(self, ctx):
        mid = await self._get_msg_id()
        if not mid:
            return await ctx.reply("ℹ️ tidak ada pin tersimpan.", mention_author=False)
        ch = self.bot.get_channel(self.channel_id) or await self.bot.fetch_channel(self.channel_id)
        if ch is None: 
            return await ctx.reply("❌ channel tidak ditemukan", mention_author=False)
        try:
            m = await ch.fetch_message(mid)
            try: await m.unpin()
            except Exception: pass
        except Exception: pass
        await self._set_msg_id(None)
        await self._set_last_ts(0)
        await ctx.reply("🧹 status pin dibersihkan.", mention_author=False)

    @status_group.command(name="rate")
    async def status_rate(self, ctx, sec: int):
        self.min_sec = max(1, int(sec))
        await ctx.reply(f"⏱️ rate limit di-set ke {self.min_sec}s", mention_author=False)


async def setup(bot):
    cog = StatusPinOverlay(bot)
    await bot.add_cog(cog)
    cog._install_patch()
    log.info("[status-pin] overlay v2 loaded")

def setup(bot):
    try:
        import asyncio
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            pass
        if loop and loop.is_running():
            return loop.create_task(setup(bot))
        else:
            return asyncio.run(setup(bot))
    except Exception:
        return None
