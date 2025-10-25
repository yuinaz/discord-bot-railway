# -*- coding: utf-8 -*-
from __future__ import annotations
import os, re, logging, asyncio, inspect
from typing import Optional, Set

try:
    import discord
    from discord.ext import commands
except Exception:
    class discord:
        class Embed: ...
        class Message: ...
    class commands:
        class Cog:
            @staticmethod
            def listener(*a, **k):
                def _w(f): return f
                return _w

LOG = logging.getLogger(__name__)

_QUE = re.compile(r"\bquestion\b.*\bleina\b", re.I)
_ANS = re.compile(r"\banswer\b", re.I)
_NAME_TRIG = re.compile(r"^\s*(leina[,:\s]|<@!?(\d+)>|@leina)", re.I)

def _iso_id() -> Optional[int]:
    raw = (os.getenv("QNA_ISOLATION_CHANNEL_ID") or os.getenv("QNA_CHANNEL_ID") or "").strip()
    raw = re.sub(r"[^\d]", "", raw)
    return int(raw) if raw.isdigit() else None

def _pick_provider_label() -> str:
    prov = (os.getenv("AI_PROVIDER", "auto") or "auto").lower()
    if prov in ("groq","g","llama","mixtral"): return "Groq"
    if prov in ("gemini","google","gai"): return "Gemini"
    return "Groq" if os.getenv("GROQ_API_KEY") else "Gemini"

def _resolve_groq_func():
    try:
        from satpambot.ml import groq_helper as gh  # type: ignore
    except Exception as e:
        LOG.debug("[qna] groq_helper import failed: %r", e); return None
    for name in ("get_groq_answer","groq_answer","ask_groq","groq_chat","get_answer","get_text"):
        fn = getattr(gh, name, None)
        if callable(fn): return fn
    return None

async def _call_llm(prompt: str, provider: str) -> Optional[str]:
    if provider == "Groq":
        fn = _resolve_groq_func()
        if not fn:
            LOG.warning("[qna] Groq helper not found"); return None
        try:
            if inspect.iscoroutinefunction(fn): return await fn(prompt)  # type: ignore
            return await asyncio.to_thread(fn, prompt)                   # type: ignore
        except TypeError:
            try:
                if inspect.iscoroutinefunction(fn): return await fn(prompt=prompt)  # type: ignore
                return await asyncio.to_thread(fn, prompt=prompt)                   # type: ignore
            except Exception as e:
                LOG.warning("[qna] Groq signature mismatch: %r", e); return None
        except Exception as e:
            LOG.warning("[qna] Groq call failed: %r", e); return None
    else:
        try:
            from satpambot.ai.gemini_client import generate_text as _gemini_answer  # type: ignore
            return await asyncio.to_thread(_gemini_answer, prompt)
        except Exception as e:
            LOG.warning("[qna] Gemini call failed: %r", e); return None

def _gate_public_allowed() -> bool:
    try:
        from pathlib import Path as _Path
        from satpambot.shared.progress_gate import ProgressGate  # type: ignore
        return ProgressGate(_Path("data/progress_gate.json")).is_public_allowed()
    except Exception:
        return True

def _strip_mention(text: str, me_id: Optional[int]) -> str:
    text = text or ""
    if me_id: text = re.sub(fr"<@!?\s*{me_id}\s*>", "", text, flags=re.I).strip()
    return re.sub(r"^\s*leina[,:\s]+", "", text, flags=re.I).strip()

class QnaPublicAutoAnswer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._answered_ids: Set[int] = set()

    @commands.Cog.listener()
    async def on_message(self, m: "discord.Message"):
        try:
            iso = _iso_id()
            ch_id = getattr(getattr(m, "channel", None), "id", None)
            if not ch_id: return

            # ===== MODE A: channel isolasi =====
            if iso and ch_id == iso:
                e = m.embeds[0] if getattr(m, "embeds", None) else None
                title = (getattr(e,"title","") or "").strip()
                author = (getattr(getattr(e,"author",None),"name","") or "").strip()
                desc = (getattr(e,"description","") or "").strip()
                combo = " ".join([title, author, desc]).lower()

                if not e or not _QUE.search(combo) or _ANS.search(combo) or m.id in self._answered_ids:
                    return

                provider = _pick_provider_label()
                prompt = desc or title
                if not prompt: return

                try: await m.channel.typing().__aenter__();  ans = await _call_llm(prompt, provider)
                finally:
                    try: await m.channel.typing().__aexit__(None,None,None)
                    except Exception: pass
                if not ans: return
                self._answered_ids.add(m.id)
                emb = discord.Embed(title=f"Answer by {provider}", description=ans)
                await m.channel.send(embed=emb, reference=m)
                return

            # ===== MODE B: channel publik =====
            if not getattr(m.author, "bot", False):
                content = getattr(m, "content", "") or ""
                me_id = getattr(getattr(self.bot, "user", None), "id", None)
                mentioned = any(getattr(u, "id", None) == me_id for u in (getattr(m, "mentions", None) or []))
                if iso and ch_id == iso: return  # safety
                if mentioned or _NAME_TRIG.search(content):
                    if not _gate_public_allowed(): return
                    provider = _pick_provider_label()
                    prompt = _strip_mention(content, me_id)
                    if not prompt: return
                    try: await m.channel.typing().__aenter__();  ans = await _call_llm(prompt, provider)
                    finally:
                        try: await m.channel.typing().__aexit__(None,None,None)
                        except Exception: pass
                    if not ans: return
                    emb = discord.Embed(title="Answer by Leina", description=ans)
                    emb.set_footer(text=f"Powered by {provider}")
                    await m.channel.send(embed=emb, reference=m)
        except Exception as ex:
            LOG.warning("[qna-dualmode] fail: %r", ex)

async def setup(bot):
    await bot.add_cog(QnaPublicAutoAnswer(bot))
