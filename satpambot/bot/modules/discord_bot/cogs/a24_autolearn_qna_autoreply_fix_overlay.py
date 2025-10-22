import os, re, time, json, logging, hashlib
import discord
from discord.ext import commands

log = logging.getLogger(__name__)
MAX_FIELD = 1024

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())

def _hash(s: str) -> str:
    return hashlib.sha1(_norm(s).encode()).hexdigest()

async def _get(url, token, key):
    if not (url and token): return None
    try:
        import aiohttp
        async with aiohttp.ClientSession() as sess:
            r = await sess.get(f"{url}/get/{key}", headers={"Authorization": f"Bearer {token}"}, timeout=8)
            if r.status == 200:
                j = await r.json()
                return (j or {}).get("result")
    except Exception:
        return None

async def _setex(url, token, key, ttl, val):
    if not (url and token): return False
    try:
        import aiohttp
        async with aiohttp.ClientSession() as sess:
            r = await sess.post(f"{url}/setex/{key}/{ttl}/{val}", headers={"Authorization": f"Bearer {token}"}, timeout=8)
            return r.status == 200
    except Exception:
        return False

async def _llm(bot, q: str, providers):
    # 1) prefer bot.llm_ask if exists
    fn = getattr(bot, "llm_ask", None)
    if callable(fn):
        for prov in providers:
            try:
                try: txt = await fn(q, provider=prov)
                except TypeError: txt = await fn(q)
                if txt: return txt, prov
            except Exception as e:
                log.debug("[autolearn-fix] bot.llm_ask %s failed: %r", prov, e)
    # 2) fallback to direct (import-lazy to avoid import error at import time)
    try:
        from ..helpers.llm_fallback_min import groq_chat, gemini_chat
    except Exception:
        groq_chat = gemini_chat = None
    for prov in providers:
        try:
            if prov == "gemini" and gemini_chat:
                txt = await gemini_chat(q, system="Jawab singkat dan jelas. Bahasa Indonesia.")
            elif prov == "groq" and groq_chat:
                txt = await groq_chat(q, system="Jawab singkat dan jelas. Bahasa Indonesia.")
            else:
                continue
            if txt: return txt, prov
        except Exception as e:
            log.debug("[autolearn-fix] direct %s failed: %r", prov, e)
    return "", ""

class AutoLearnQnAAutoReplyFixOverlay(commands.Cog):
    """Auto-reply Q->A di channel QnA. Import-safe, tidak crash bila config/ENV kosong."""
    def __init__(self, bot):
        self.bot = bot
        # channel id dari env atau default (1426571542627614772)
        try:
            self.QID = int(os.getenv("QNA_CHANNEL_ID","1426571542627614772"))
        except Exception:
            self.QID = 1426571542627614772
        # provider order dari env atau default
        prov = os.getenv("QNA_PROVIDER_ORDER","groq,gemini")
        self.providers = [p.strip().lower() for p in prov.split(",") if p.strip()]
        # upstash (opsional)
        self.url = (os.getenv("UPSTASH_REDIS_REST_URL","") or "").rstrip("/") or None
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN") or None
        self.ns = os.getenv("QNA_ANSWER_DEDUP_NS","qna:answered")
        try:
            self.ttl = int(os.getenv("QNA_ANSWER_TTL_SEC","86400"))
        except Exception:
            self.ttl = 86400
        log.info("[autolearn-fix] channel=%s providers=%s", self.QID, self.providers)

    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        try:
            if not m or not hasattr(m, "content"): return
            if getattr(m, "author", None) and getattr(m.author, "bot", False): return
            if not m.channel or int(m.channel.id) != self.QID: return
            q = (m.content or "").strip()
            if not q: return

            h = _hash(q)
            if await _get(self.url, self.token, f"{self.ns}:{h}") is not None:
                return

            ans, src = await _llm(self.bot, q, self.providers)
            if not ans: return

            e = discord.Embed(title="[auto-learn]", color=0x3b82f6)
            e.add_field(name="Q", value=q[:MAX_FIELD], inline=False)
            e.add_field(name=f"A · {src}", value=ans[:MAX_FIELD], inline=False)
            await m.channel.send(embed=e)

            await _setex(self.url, self.token, f"{self.ns}:{h}", self.ttl, str(int(time.time())))
            # best-effort XP award
            for name in ("satpam_xp", "xp_add", "xp_award"):
                fn = getattr(self.bot, name, None)
                if callable(fn):
                    try:
                        fn(int(m.author.id), 5, "autolearn:answer")
                        break
                    except TypeError:
                        try:
                            fn(int(m.author.id), 5)
                            break
                        except Exception:
                            pass
        except Exception as e:
            log.debug("[autolearn-fix] on_message error: %r", e)

async def setup(bot):
    await bot.add_cog(AutoLearnQnAAutoReplyFixOverlay(bot))
