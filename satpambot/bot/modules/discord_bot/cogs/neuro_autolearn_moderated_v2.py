from __future__ import annotations
import os, json, logging, asyncio, random, time, hashlib
from datetime import datetime, timezone
from typing import Optional

try:
    import discord
    from discord.ext import commands, tasks
except Exception:  # smoke-safe
    class discord:  # type: ignore
        class Embed:
            def __init__(self, *a, **k): ...
            def set_author(self, **k): ...
            def set_footer(self, **k): ...
        class Message: ...
    class commands:  # type: ignore
        class Cog:
            @staticmethod
            def listener(*a, **k):
                def _w(f): return f
                return _w
        @staticmethod
        def listener(*a, **k):
            def _w(f): return f
            return _w
    class tasks:  # type: ignore
        @staticmethod
        def loop(seconds=60):
            def _wrap(fn): return fn
            return _wrap

try:
    from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
except Exception:
    UpstashClient = None

log = logging.getLogger(__name__)

def _cfg_int(name: str, default: Optional[int]=None) -> Optional[int]:
    v = os.getenv(name, "")
    try:
        return int(v) if v else default
    except Exception:
        return default

def _cfg_str(name: str, default: str="") -> str:
    return os.getenv(name, default)

def _read_topics(path: str) -> list[str]:
    try:
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    flat = []
    if isinstance(data, dict):
        for _, items in data.items():
            if isinstance(items, list):
                flat.extend([str(x).strip() for x in items if str(x).strip()])
    elif isinstance(data, list):
        flat = [str(x).strip() for x in data if str(x).strip()]
    # unique while preserving order
    seen = set(); uniq = []
    for q in flat:
        if q not in seen:
            seen.add(q); uniq.append(q)
    return uniq

def _h(s: str) -> str:
    import hashlib; return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]

def _q_embed(q: str) -> "discord.Embed":
    e = discord.Embed(title="Question by Leina", description=q[:4000])
    e.set_author(name="Leina — auto-learn")
    e.set_footer(text="QNA_AUTOLEARN")
    return e

def _a_embed(p: str, a: str) -> "discord.Embed":
    e = discord.Embed(title=f"Answer by {p.upper()}", description=a[:4000])
    e.set_author(name="Leina — QnA")
    e.set_footer(text=f"QNA_PROVIDER:{p.upper()}")
    return e

async def _ask_groq(q: str) -> str:
    key = os.getenv("GROQ_API_KEY") or ""
    if not key: raise RuntimeError("GROQ_API_KEY tidak di-set")
    model = os.getenv("GROQ_MODEL") or "llama-3.1-8b-instant"
    url = os.getenv("GROQ_BASE_URL","https://api.groq.com/openai/v1") + "/chat/completions"
    payload = {"model": model, "temperature": 0.2, "max_tokens": 300,
               "messages":[{"role":"system","content":"Jawab singkat, to the point, aman."},
                           {"role":"user","content": q.strip()[:4000]}]}
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30) as cli:
            r = await cli.post(url, headers={"Authorization": f"Bearer {key}"}, json=payload)
            r.raise_for_status(); d = r.json()
            return (d.get("choices",[{}])[0].get("message",{}).get("content","") or "").strip()
    except Exception:
        import requests
        def _do():
            r=requests.post(url,headers={"Authorization":f"Bearer {key}"},json=payload,timeout=30)
            r.raise_for_status(); return r.json()
        d = await asyncio.to_thread(_do)
        return (d.get("choices",[{}])[0].get("message",{}).get("content","") or "").strip()

async def _ask_gemini(q: str) -> str:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    model = os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"
    try:
        from google import genai
        cli = genai.Client(api_key=key) if key else genai.Client()
        resp = cli.models.generate_content(model=model, contents=q.strip()[:4000])
        return getattr(resp, "text", "") or ""
    except Exception:
        import httpx
        base = os.getenv("GEMINI_BASE_URL","https://generativelanguage.googleapis.com")
        path = f"/v1beta/models/{model}:generateContent?key={key}"
        body = {"contents":[{"parts":[{"text": q.strip()[:4000]}]}]}
        async with httpx.AsyncClient(timeout=30) as cli:
            r = await cli.post(base+path, json=body); r.raise_for_status(); d = r.json()
            try: return (d["candidates"][0]["content"]["parts"][0]["text"]).strip()
            except Exception: return ""

class NeuroAutolearnModeratedV2(commands.Cog):
    """Private auto-learn QnA. Uses data/config/qna_topics.json. Posts 'Question by Leina' then 'Answer by GROQ/GEMINI'."""
    def __init__(self, bot):
        self.bot = bot
        self.qna_channel_id = _cfg_int("QNA_CHANNEL_ID", None)  # private channel
        self.provider = (_cfg_str("QNA_PROVIDER","groq") or "groq").lower()
        self.topics_path = _cfg_str("QNA_TOPICS_PATH","data/config/qna_topics.json")
        self.period = int(_cfg_str("AUTOLEARN_PERIOD_SEC","60"))
        self._mem = {}  # hash -> ts
        self._ns = _cfg_str("QNA_AUTOLEARN_IDEM_NS","qna:asked")
        self._loop.start()
        log.info("[autolearn] ch=%s provider=%s topics=%s period=%s", self.qna_channel_id, self.provider, self.topics_path, self.period)

    async def _asked(self, q: str) -> bool:
        h=_h(q)
        if h in self._mem and time.time()-self._mem[h] < 24*3600: return True
        try:
            if UpstashClient:
                cli=UpstashClient()
                if getattr(cli,"enabled",False):
                    k=f"{self._ns}:{h}"
                    if await cli.get_raw(k) is not None: return True
                    await cli.setex(k, 60*60*24*30, "1")
        except Exception: pass
        self._mem[h]=time.time(); return False

    def _pick_q(self)->Optional[str]:
        qs=_read_topics(self.topics_path)
        if not qs: return None
        random.shuffle(qs)
        for q in qs:
            q=q.strip()
            if not q: continue
            if not q.endswith("?"): q=q+"?"
            return q
        return None

    async def _tick(self):
        ch = self.bot.get_channel(self.qna_channel_id) if self.qna_channel_id else None
        if ch is None and self.qna_channel_id:
            try: ch = await self.bot.fetch_channel(self.qna_channel_id)
            except Exception: return
        q = self._pick_q()
        if not q or await self._asked(q): return
        try:
            qm = await ch.send(embed=_q_embed(q))
        except Exception: return
        try:
            if self.provider.startswith("groq"):
                a = await _ask_groq(q); p="groq"
            else:
                a = await _ask_gemini(q); p="gemini"
            if not a.strip(): a="Maaf, belum ada jawaban."
            await asyncio.sleep(0.2)
            try: await qm.reply(embed=_a_embed(p,a), mention_author=False)
            except Exception: await ch.send(embed=_a_embed(p,a))
        except Exception: pass

    @tasks.loop(seconds=30)
    async def _loop(self):
        now = int(datetime.now(timezone.utc).timestamp())
        if self.period and now % self.period != 0: return
        try: await self._tick()
        except Exception: log.error("[autolearn] tick error", exc_info=True)

    @_loop.before_loop
    async def _before(self): 
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(NeuroAutolearnModeratedV2(bot))
