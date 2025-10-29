# -*- coding: utf-8 -*-
from __future__ import annotations
import os, re, asyncio, logging
from typing import Optional, Tuple
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name); return v if v not in (None, "") else default

def _qna_id() -> Optional[int]:
    try: v = int(_env("QNA_CHANNEL_ID","0") or "0"); return v or None
    except Exception: return None

def _provider_order() -> list[str]:
    raw = _env("QNA_PROVIDER_ORDER", "gemini,groq") or "gemini,groq"
    return [x.strip().lower() for x in re.split(r"[\s,]+", raw) if x.strip()]

def _has_gemini() -> bool:
    for k in ("GEMINI_API_KEY","GOOGLE_API_KEY","GOOGLE_GENAI_API_KEY","GOOGLE_AI_API_KEY"):
        if os.getenv(k): return True
    return False

def _has_groq() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))

async def _call_llm(topic: str) -> Tuple[str, str]:
    picked = "fallback"
    try:
        from satpambot.bot.providers.llm import LLM; llm = LLM()
        order = _provider_order() or ["gemini","groq"]
        log.info("[qna-answer] providers=%s", order)
        for p in order:
            p = p.lower()
            try:
                if p.startswith("gem") and _has_gemini():
                    picked="gemini"
                    ans = await llm.chat_gemini(prompt=topic, messages=None, system_prompt=None, temperature=0.2, max_tokens=None)
                    if ans: return ("gemini", ans)
                if p.startswith(("groq","llama","mixtral","grok")) and _has_groq():
                    picked="groq"
                    ans = await llm.chat_groq(prompt=topic, messages=None, system_prompt=None, temperature=0.2, max_tokens=None)
                    if ans: return ("groq", ans)
            except Exception as e:
                log.warning("[qna-answer] provider %s failed: %r", p, e)
                await asyncio.sleep(0.1)
        # generic
        try:
            ans = await llm.chat(prompt=topic, messages=None, system_prompt=None, temperature=0.2, max_tokens=None)
            if ans: return (picked, ans)
        except Exception as e:
            log.warning("[qna-answer] llm.chat fallback failed: %r", e)
    except Exception as e:
        log.warning("[qna-answer] LLM provider missing: %r", e)
    # hard fallback text
    return ("fallback", "Maaf, provider QnA belum aktif atau kuncinya belum diset.")

def _blue_colour() -> int:
    try: return discord.Colour.blue().value
    except Exception: return 0x3366FF

class QnaAutoAnswerOverlay(commands.Cog):
    def __init__(self, bot): self.bot = bot; self.qna_id = _qna_id()

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
            if not getattr(m, "embeds", None) or len(m.embeds) == 0: return
            e = m.embeds[0]
            if not self._is_question_embed(e): return
            topic = self._extract_topic(e) or "Jelaskan secara singkat."
            log.info("[qna-answer] detected question mid=%s topic=%r", getattr(m,"id",None), topic[:80])
            prov, text = await _call_llm(topic)
            emb = discord.Embed(title=f"Answer by {prov.capitalize()}", description=text, colour=_blue_colour())
            try:
                await m.reply(embed=emb, mention_author=False)
                log.info("[qna-answer] replied with %s", prov)
            except Exception as e1:
                try:
                    await ch.send(embed=emb)
                    log.info("[qna-answer] sent with %s (fallback)", prov)
                except Exception as e2:
                    log.warning("[qna-answer] send failed: %r / %r", e1, e2)
        except Exception as exc:
            log.warning("[qna-answer] on_message fail: %r", exc)

async def setup(bot): await bot.add_cog(QnaAutoAnswerOverlay(bot))