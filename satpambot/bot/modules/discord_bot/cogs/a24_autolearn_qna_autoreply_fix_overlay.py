
from __future__ import annotations
import os, re, json, asyncio, logging, hashlib, time
from typing import Optional, List, Tuple
import discord
from discord.ext import commands
try:
    import aiohttp
except Exception:
    aiohttp = None

from ..helpers.config_defaults import env, env_int

LOG = logging.getLogger(__name__)

def _channels_allowlist() -> List[int]:
    raw = env("QNA_CHANNEL_ALLOWLIST", env("QNA_CHANNEL_ID"))
    ids = []
    for tok in re.split(r"[,\s]+", raw or ""):
        tok = tok.strip()
        if tok.isdigit():
            try: ids.append(int(tok))
            except Exception: pass
    return ids

def _provider_order() -> List[str]:
    raw = env("QNA_PROVIDER_ORDER", "groq,gemini")
    return [p.strip().lower() for p in (raw or "").split(",") if p.strip()]

def _hash(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()

def _dedup_key(question: str) -> str:
    ns = env("QNA_ANSWER_DEDUP_NS","qna:answered")
    return f"{ns}:{_hash(question.strip().lower())}"

class AutoLearnQnAAutoReplyFix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None
        self.allow_channels = set(_channels_allowlist())
        self.answer_ttl = env_int("QNA_ANSWER_TTL_SEC", 86400)
        self.xp_award = env_int("QNA_XP_AWARD", 5)

    async def _ensure_session(self):
        if self.session is None and aiohttp is not None:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=25))

    def cog_unload(self):
        if self.session and not self.session.closed:
            asyncio.create_task(self.session.close())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message or not message.guild or not message.embeds:
            return
        if self.allow_channels and (message.channel.id not in self.allow_channels):
            return
        try:
            if not message.author.bot or message.author.id != self.bot.user.id:
                return
        except Exception:
            return

        q = self._extract_question(message)
        if not q:
            return
        if await self._is_answered(q):
            return

        text, prov = await self._answer(q)
        if not text:
            LOG.warning("[autolearn-qna] providers failed to answer")
            return

        title = f"Answer by {prov.capitalize()}" if prov else "Answer by Leina"
        desc = text.strip() + "\n\n" + f"*Q: {q.strip()}*"
        em = discord.Embed(title=title, description=desc)
        if prov:
            em.set_footer(text=f"via {prov.capitalize()}")
        try:
            await message.reply(embed=em, mention_author=False)
        except Exception as e:
            LOG.warning("[autolearn-qna] failed to reply: %r", e)
            return

        await self._mark_answered(q)
        await self._award_xp(self.xp_award)

    def _extract_question(self, message: discord.Message) -> Optional[str]:
        try:
            for em in message.embeds:
                if (em.title or "").strip().lower() == "question by leina":
                    return (em.description or "").strip()
        except Exception:
            pass
        return None

    async def _is_answered(self, q: str) -> bool:
        if aiohttp is None: return False
        await self._ensure_session()
        url = env("UPSTASH_REDIS_REST_URL",""); tok=env("UPSTASH_REDIS_REST_TOKEN","")
        if not (url and tok): return False
        key = _dedup_key(q)
        try:
            payload = json.dumps([["EXISTS", key]])
            async with self.session.post(f"{url}/pipeline",
                headers={"Authorization": f"Bearer {tok}","Content-Type": "application/json"},
                data=payload) as r:
                data = await r.json()
                return bool(data and data[0].get("result"))
        except Exception:
            return False

    async def _mark_answered(self, q: str):
        if aiohttp is None: return
        await self._ensure_session()
        url = env("UPSTASH_REDIS_REST_URL",""); tok=env("UPSTASH_REDIS_REST_TOKEN","")
        if not (url and tok): return
        key = _dedup_key(q)
        try:
            payload = json.dumps([["SETEX", key, str(self.answer_ttl), "1"]])
            async with self.session.post(f"{url}/pipeline",
                headers={"Authorization": f"Bearer {tok}","Content-Type": "application/json"},
                data=payload) as r:
                await r.read()
        except Exception:
            pass

    async def _award_xp(self, amt: int):
        if amt <= 0 or aiohttp is None: return
        url = env("UPSTASH_REDIS_REST_URL",""); tok=env("UPSTASH_REDIS_REST_TOKEN","")
        if not (url and tok): return
        key = env("XP_SENIOR_KEY","xp:bot:senior_total_v2")
        try:
            await self._ensure_session()
            payload = json.dumps([["INCRBY", key, str(amt)]])
            async with self.session.post(f"{url}/pipeline",
                headers={"Authorization": f"Bearer {tok}","Content-Type":"application/json"},
                data=payload) as r:
                await r.read()
            LOG.info("[autolearn-qna] XP +%d → %s", amt, key)
        except Exception as e:
            LOG.debug("[autolearn-qna] xp award fail: %r", e)

    async def _answer(self, question: str) -> Tuple[Optional[str], Optional[str]]:
        for p in _provider_order():
            try:
                if p == "groq":
                    ans = await self._ask_groq(question)
                elif p == "gemini":
                    ans = await self._ask_gemini(question)
                else:
                    ans = None
                if ans: return ans.strip(), p
            except Exception as e:
                LOG.warning("[autolearn-qna] provider %s failed: %r", p, e)
        return None, None

    async def _ask_groq(self, question: str) -> Optional[str]:
        key = env("GROQ_API_KEY",""); model = env("GROQ_MODEL","llama-3.1-8b-instant")
        if not key or aiohttp is None: return None
        await self._ensure_session()
        url = "https://api.groq.com/openai/v1/chat/completions"
        body = {"model": model, "messages":[{"role":"user","content": question}], "temperature":0.7, "max_tokens":512}
        async with self.session.post(url, json=body, headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"}) as r:
            data = await r.json()
        try: return data["choices"][0]["message"]["content"]
        except Exception: return None

    async def _ask_gemini(self, question: str) -> Optional[str]:
        key = env("GEMINI_API_KEY",""); model = env("GEMINI_MODEL","gemini-2.5-flash-lite")
        if not key or aiohttp is None: return None
        await self._ensure_session()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        body = {"contents":[{"parts":[{"text": question}]}]}
        async with self.session.post(url, json=body, headers={"Content-Type":"application/json"}) as r:
            data = await r.json()
        try: return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception: return None

async def setup(bot):
    await bot.add_cog(AutoLearnQnAAutoreplyFix(bot))


# Legacy sync setup wrapper (smoketest-friendly)
def setup(bot):
    try:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            return loop.create_task(setup(bot))  # schedule async setup
        else:
            return asyncio.run(setup(bot))
    except Exception:
        return None
