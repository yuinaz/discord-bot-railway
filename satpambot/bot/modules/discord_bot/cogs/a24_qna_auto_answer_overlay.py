from __future__ import annotations
import os, re, logging, asyncio
from typing import Optional

try:
    import discord
    from discord.ext import commands
except Exception:
    class discord:  # minimal stubs for tests
        class Embed: ...
        class Message: ...
    class commands:
        class Cog:
            @staticmethod
            def listener(*a, **k):
                def _w(f): return f
                return _w

log = logging.getLogger(__name__)

# Patterns
_QUE = re.compile(r"\bquestion\b.*\bleina\b", re.I)
_ANS = re.compile(r"\banswer\b", re.I)
_NAME_TRIG = re.compile(r"^\s*(leina[,:\s]|<@!?(\d+)>|@leina)", re.I)

def _iso_id() -> Optional[int]:
    # Accept either QNA_ISOLATION_CHANNEL_ID or QNA_CHANNEL_ID
    for var in ("QNA_ISOLATION_CHANNEL_ID", "QNA_CHANNEL_ID"):
        v = os.getenv(var) or ""
        v = v.strip()
        if v.isdigit():
            return int(v)
    return None

def _pick_provider_label() -> str:
    prov = (os.getenv("AI_PROVIDER", "auto") or "auto").lower()
    if prov in ("groq","g","llama","mixtral"): return "Groq"
    if prov in ("gemini","google","gai"): return "Gemini"
    return "Groq" if os.getenv("GROQ_API_KEY") else "Gemini"

async def _call_llm(prompt: str, provider_label: str) -> Optional[str]:
    if provider_label == "Groq":
        try:
            from satpambot.ml.groq_helper import get_groq_answer as _groq_answer
            return await asyncio.to_thread(_groq_answer, prompt)
        except Exception as e:
            log.warning("[qna] Groq call failed: %r", e)
            return None
    else:
        try:
            from satpambot.ai.gemini_client import generate_text as _gemini_answer
            return await asyncio.to_thread(_gemini_answer, prompt)
        except Exception as e:
            log.warning("[qna] Gemini call failed: %r", e)
            return None

def _gate_public_allowed() -> bool:
    # Soft dependency; if ProgressGate is missing, allow
    try:
        from pathlib import Path as _Path
        from satpambot.shared.progress_gate import ProgressGate
        return ProgressGate(_Path("data/progress_gate.json")).is_public_allowed()
    except Exception:
        return True

def _strip_mention(text: str, me_id: Optional[int]) -> str:
    text = text or ""
    if me_id:
        text = re.sub(fr"<@!?\s*{me_id}\s*>", "", text, flags=re.I).strip()
    # Remove 'leina,' at the start
    return re.sub(r"^\s*leina[,:\s]+", "", text, flags=re.I).strip()

class QnaPublicAutoAnswer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, m: "discord.Message"):
        try:
            # ignore our own followup messages
            if getattr(m.author, "id", None) == getattr(getattr(self.bot, "user", None), "id", None):
                pass  # continue checks below (needed to inspect embeds from autoprompt)
            iso = _iso_id()
            ch_id = getattr(getattr(m, "channel", None), "id", None)

            # MODE A: isolation channel -> Answer provider to "Question by Leina"
            if iso and ch_id == iso and getattr(m, "embeds", None):
                e = m.embeds[0] if m.embeds else None
                if e:
                    def g(x): return (x or "").strip().lower()
                    txt = " ".join([g(getattr(e,"title","")), g(getattr(getattr(e,"author",None),"name",None)), g(getattr(e,"description",""))])
                    if _QUE.search(txt) and not _ANS.search(txt):
                        provider = _pick_provider_label()
                        prompt = getattr(e, "description", "") or getattr(e, "title", "")
                        if not prompt:
                            return
                        try:
                            await m.channel.typing().__aenter__()
                        except Exception: pass
                        ans = await _call_llm(prompt, provider)
                        try: await m.channel.typing().__aexit__(None, None, None)
                        except Exception: pass
                        if not ans: return
                        emb = discord.Embed(title=f"Answer by {provider}", description=ans)
                        await m.channel.send(embed=emb, reference=m)
                        return

            # MODE B: public mention -> Answer by Leina (content from LLM), gated
            if ch_id != iso and not getattr(m.author, "bot", False):
                content = getattr(m, "content", "") or ""
                me_id = getattr(getattr(self.bot, "user", None), "id", None)
                if (getattr(m, "mentions", None) and any(getattr(u, "id", None) == me_id for u in m.mentions)) or _NAME_TRIG.search(content):
                    if not _gate_public_allowed():
                        return
                    provider = _pick_provider_label()
                    prompt = _strip_mention(content, me_id)
                    if not prompt:
                        return
                    try:
                        await m.channel.typing().__aenter__()
                    except Exception: pass
                    ans = await _call_llm(prompt, provider)
                    try: await m.channel.typing().__aexit__(None, None, None)
                    except Exception: pass
                    if not ans: return
                    emb = discord.Embed(title="Answer by Leina", description=ans)
                    emb.set_footer(text=f"Powered by {provider}")
                    await m.channel.send(embed=emb, reference=m)
        except Exception as ex:
            log.warning("[qna-dualmode] fail: %r", ex)

async def setup(bot):
    await bot.add_cog(QnaPublicAutoAnswer(bot))
