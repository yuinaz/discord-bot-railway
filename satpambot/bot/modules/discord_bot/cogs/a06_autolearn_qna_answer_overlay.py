# -*- coding: utf-8 -*-
from __future__ import annotations
import os, re, asyncio, logging
from typing import Optional, Tuple
try:
    import discord
    from discord.ext import commands
except Exception:
    class discord:  # type: ignore
        class Message: ...
        class Embed:
            def __init__(self, *a, **k): self.title=""; self.description=""; self.colour=0
            def set_footer(self, **k): pass
    class commands:  # type: ignore
        class Cog: ...
        @staticmethod
        def listener(*a, **k):
            def _f(fn): return fn
            return _f
log = logging.getLogger(__name__)
def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name); return v if v not in (None, "") else default
def _qna_id() -> Optional[int]:
    try: v = int(_env("QNA_CHANNEL_ID","0") or "0"); return v or None
    except Exception: return None
def _provider_order() -> list[str]:
    raw = _env("QNA_PROVIDER_ORDER", "gemini,groq") or "gemini,groq"
    import re as _re; return [x.strip().lower() for x in _re.split(r"[\s,]+", raw) if x.strip()]
def _has_gemini() -> bool:
    for k in ("GEMINI_API_KEY","GOOGLE_API_KEY","GOOGLE_GENAI_API_KEY","GOOGLE_AI_API_KEY"):
        if os.getenv(k): return True
    return False
def _has_groq() -> bool: return bool(os.getenv("GROQ_API_KEY"))
async def _dedup_mark(mid: int) -> bool:
    try:
        from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
        cli = UpstashClient()
        if not getattr(cli, "enabled", False): return True
        key = f"qna:answered:{int(mid)}"
        if await cli.get_raw(key) is not None: return False
        await cli.setex(key, 60*60*24*30, "1"); return True
    except Exception as e:
        log.debug("[qna-answer] dedup mark err: %r", e); return True
async def _call_llm(topic: str) -> Tuple[str, str]:
    try:
        from satpambot.bot.providers.llm import LLM; llm = LLM()
    except Exception as e:
        log.warning("[qna-answer] LLM provider missing: %r", e); return ("fallback", "Maaf, LLM tidak tersedia saat ini.")
    order = _provider_order() or ["gemini","groq"]
    for p in order:
        p = p.lower()
        try:
            if p.startswith("gem") and _has_gemini():
                ans = await llm.chat_gemini(prompt=topic, messages=None, system_prompt=None, temperature=0.2, max_tokens=None)
                if ans: return ("gemini", ans)
            if p.startswith(("groq","llama","mixtral","grok")) and _has_groq():
                ans = await llm.chat_groq(prompt=topic, messages=None, system_prompt=None, temperature=0.2, max_tokens=None)
                if ans: return ("groq", ans)
        except Exception as e:
            log.warning("[qna-answer] provider %s failed: %r", p, e); await asyncio.sleep(0.1); continue
    try:
        ans = await llm.chat(prompt=topic, messages=None, system_prompt=None, temperature=0.2, max_tokens=None)
        if ans: return ("fallback", ans)
    except Exception as e:
        log.warning("[qna-answer] llm.chat auto failed: %r", e)
    return ("fallback", "Maaf, provider QnA sedang tidak tersedia. Coba lagi nanti ya.")
class QnaAutoAnswerOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot; self.qna_id = _qna_id()
    def _is_question_embed(self, e: "discord.Embed") -> bool:
        title = (getattr(e, "title", "") or "").strip().lower()
        return title.startswith("question by leina")
    def _extract_topic(self, e: "discord.Embed") -> Optional[str]:
        desc = getattr(e, "description", None)
        if desc: return desc.strip()
        try:
            for f in (getattr(e, "fields", []) or []):
                n = (getattr(f, "name","") or "").lower()
                if "question" in n:
                    v = (getattr(f,"value","") or "").strip()
                    if v: return v
        except Exception: pass
        return None
    @commands.Cog.listener()
    async def on_message(self, m: "discord.Message"):
        try:
            if not self.qna_id: return
            ch = getattr(m, "channel", None)
            if getattr(ch, "id", None) != self.qna_id: return
            if not getattr(m, "embeds", None): return
            if len(m.embeds) == 0: return
            e = m.embeds[0]
            if not self._is_question_embed(e): return
            if not await _dedup_mark(int(m.id)): return
            topic = self._extract_topic(e) or "Jelaskan secara singkat."
            prov, text = await _call_llm(topic)
            colour = getattr(discord, "Colour", type("C",(),{"blue":lambda:0x3366ff}))().blue() if hasattr(getattr(discord,"Colour",None),"blue") else 0
            ans = discord.Embed(title=f"Answer by {prov.capitalize()}", description=text, colour=colour)
            ans.set_footer(text=f"qna_provider: {prov}")
            try:
                await m.reply(embed=ans, mention_author=False)
            except Exception:
                try: await ch.send(embed=ans)
                except Exception as e2: log.warning("[qna-answer] send failed: %r", e2)
        except Exception as exc:
            log.warning("[qna-answer] on_message fail: %r", exc)
async def setup(bot): await bot.add_cog(QnaAutoAnswerOverlay(bot))