
"""
Minimal, robust QnA answer → XP award overlay.
- Uses satpambot.config.auto_defaults for cfg_* (matching existing helpers)
- Safe import of Upstash client with fallback to lightweight REST client
- No side effects at import; network only inside handlers
- Default XP key unified: xp:bot:senior_total
"""
from __future__ import annotations

import logging, re, os, json, urllib.request, urllib.parse, asyncio
from typing import Optional

try:
    import discord
    from discord.ext import commands
except Exception:  # very old smoke envs
    class commands:  # type: ignore
        class Cog: ...
        def listener(*a, **k):
            def _w(f): return f
            return _w
    class discord:  # type: ignore
        class Message: ...
        class Embed: ...

# Use the config path that matches other modules (e.g., xp_total_resolver)
try:
    from satpambot.config.auto_defaults import cfg_str, cfg_int
except Exception:
    # Fallback shim
    def cfg_str(k: str, d: str=""):
        return os.getenv(k, d)
    def cfg_int(k: str, d: int=0):
        try: return int(os.getenv(k, str(d)))
        except Exception: return d

log = logging.getLogger(__name__)

# --- Lightweight Upstash client (REST) ---
class _UpstashLite:
    def __init__(self):
        self.base = (os.getenv("UPSTASH_REDIS_REST_URL") or "").rstrip("/")
        self.tok  = os.getenv("UPSTASH_REDIS_REST_TOKEN") or ""
        self.enabled = bool(self.base and self.tok)

    def _req(self, path: str) -> Optional[dict]:
        if not self.enabled: return None
        url = self.base + path
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.tok}"})
        with urllib.request.urlopen(req, timeout=15) as r:
            s = r.read().decode()
            try:
                return json.loads(s)
            except Exception:
                return {"result": s}

    async def incrby(self, key: str, delta: int) -> bool:
        if not self.enabled: return False
        try:
            _ = self._req("/incrby/" + urllib.parse.quote(key, safe="") + "/" + str(int(delta)))
            return True
        except Exception as e:
            log.warning("[qna-award] incrby failed: %r", e)
            return False

    async def get(self, key: str) -> Optional[str]:
        try:
            r = self._req("/get/" + urllib.parse.quote(key, safe=""))
            return None if r is None else r.get("result")
        except Exception:
            return None

    async def set(self, key: str, val: str) -> bool:
        try:
            _ = self._req("/set/" + urllib.parse.quote(key, safe="") + "/" + urllib.parse.quote(val, safe=""))
            return True
        except Exception:
            return False

# --- Simple detector: provider answer embed ---
_ANS_PROVIDER = re.compile(r"\banswer\s+by\s+(groq|gemini)\b", re.I)
_QUE_PAT = re.compile(r"\b(question|pertanyaan)\b", re.I)

def _is_provider_answer_embed(e: "discord.Embed") -> bool:
    def g(x): return (x or "").strip().lower()
    title = g(getattr(e, "title",""))
    author = g(getattr(getattr(e,"author",None),"name",None))
    desc = g(getattr(e,"description",""))
    foot = g(getattr(getattr(e,"footer",None),"text",None))
    hay = " ".join([title, author, desc, foot])
    if _QUE_PAT.search(hay):  # kalau embed ini pertanyaan, jangan award
        return False
    return bool(_ANS_PROVIDER.search(hay))

class QnaAnswerAwardXP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.qna_id = cfg_int("QNA_CHANNEL_ID", 0) or cfg_int("LEARNING_QNA_CHANNEL_ID", 0) or None
        self.delta = int(cfg_str("QNA_XP_PER_ANSWER_BOT", "5") or "5")
        # Unified default key (ENV/overrides tetap bisa override)
        self.senior_key = cfg_str("XP_SENIOR_KEY", "xp:bot:senior_total")
        # Client with REST fallback
        try:
            # prefer existing client if available
            from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient  # type: ignore
            self.client = UpstashClient()
            if not getattr(self.client, "enabled", False):
                self.client = _UpstashLite()
        except Exception:
            self.client = _UpstashLite()

        # In-memory idempotency (fallback)
        self._seen = set()

    async def _mark_once(self, mid: int) -> bool:
        # Persisted idempotency (optional)
        key = f"qna:awarded:answer:{mid}"
        try:
            if await self.client.get(key) is not None:
                return False
            await self.client.set(key, "1")
            return True
        except Exception:
            # fallback to in-memory guard (per process)
            if mid in self._seen:
                return False
            self._seen.add(mid)
            # auto-clear after 10 minutes
            try:
                async def _clear():
                    await asyncio.sleep(600)
                    self._seen.discard(mid)
                asyncio.create_task(_clear())
            except Exception:
                pass
            return True

    @commands.Cog.listener("on_message")
    async def _on_message(self, m: "discord.Message"):
        try:
            if self.qna_id and getattr(getattr(m,"channel",None),"id",None) != self.qna_id:
                return
            if not getattr(getattr(m,"author",None),"bot",False):
                return
            embeds = getattr(m, "embeds", None)
            if not embeds:
                return
            e = embeds[0]
            if not _is_provider_answer_embed(e):
                return
            # idempotency guard
            if not await self._mark_once(int(getattr(m,"id",0) or 0)):
                return
            if not getattr(self.client, "enabled", False):
                log.warning("[qna-award] client disabled; skip award")
                return
            ok = await self.client.incrby(self.senior_key, int(self.delta))
            if ok:
                log.info("[qna-award] +%s XP key=%s msg=%s", self.delta, self.senior_key, getattr(m,"id",None))
            else:
                log.warning("[qna-award] incrby failed (client returned False)")
        except Exception as exc:
            log.warning("[qna-award] failed: %r", exc)

async def setup(bot):
    await bot.add_cog(QnaAnswerAwardXP(bot))
