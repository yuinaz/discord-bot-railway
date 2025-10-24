from __future__ import annotations
import os, re, asyncio, logging, time
from typing import Optional

try:
    import discord
    from discord.ext import commands
except Exception:
    class discord:  # type: ignore
        class Message: ...
        class Embed:
            def __init__(self, *a, **k): ...
            title = ''; description = ''; author = type('A', (), {'name': ''})()
            footer = type('F', (), {'text': ''})()
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

from satpambot.config.auto_defaults import cfg_int, cfg_str
log = logging.getLogger(__name__)

QNA_CHANNEL_ID = cfg_int('QNA_CHANNEL_ID', None)
WINDOW_SEC = int(cfg_str('QNA_DEDUPE_WINDOW_SEC', '900') or '900')
HIST_LIMIT = int(cfg_str('QNA_DEDUPE_HISTORY', '30') or '30')
DELETE_NON_EMBED = (cfg_str('QNA_DELETE_NON_EMBED', '1') or '1').lower() in ('1','true','yes','on')

_RX_Q = re.compile(r'\\b(question|pertanyaan)\\b', re.I)
_RX_A_PROVIDER = re.compile(r'\\banswer\\s+by\\s+(groq|gemini)\\b', re.I)

def _text_of_embed(e: 'discord.Embed') -> str:
    def g(x): return (x or '').strip().lower()
    title = g(getattr(e, 'title', ''))
    author = g(getattr(getattr(e, 'author', None), 'name', None))
    desc = g(getattr(e, 'description', ''))
    foot = g(getattr(getattr(e, 'footer', None), 'text', None))
    return ' '.join([title, author, desc, foot])

def _is_question(e: 'discord.Embed') -> bool:
    t = _text_of_embed(e)
    if _RX_A_PROVIDER.search(t): return False
    return _RX_Q.search(t) is not None

def _is_answer(e: 'discord.Embed') -> Optional[str]:
    t = _text_of_embed(e)
    m = _RX_A_PROVIDER.search(t)
    if m: return m.group(1).lower()
    if 'qna_provider:' in t:
        if 'groq' in t: return 'groq'
        if 'gemini' in t: return 'gemini'
    return None

def _norm(s: str) -> str:
    s = (s or '').strip().lower()
    s = re.sub(r'\\s+', ' ', s)
    return s

async def _safe_delete(msg: 'discord.Message'):
    try:
        await msg.delete(); return True
    except Exception as e:
        log.debug('[qna-dedupe] delete fail: %r', e); return False

class QnaDedupeAutolearn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.qid = QNA_CHANNEL_ID
        log.info('[qna-dedupe] ready; ch=%s', self.qid)

    async def _scan_and_dedupe(self, m: 'discord.Message'):
        ch = m.channel
        hist = getattr(ch, 'history', None)
        if not callable(hist): return
        now = time.time()
        try:
            async for old in ch.history(limit=HIST_LIMIT, oldest_first=False):
                if old.id == m.id: continue
                if not getattr(old, 'author', None) or not getattr(old.author, 'bot', False): continue
                if not getattr(old, 'embeds', None) or len(old.embeds) == 0: continue
                e_old = old.embeds[0]
                ts = getattr(old, 'created_at', None)
                age = now - (ts.timestamp() if hasattr(ts, 'timestamp') else 0)
                if age > WINDOW_SEC: break
                e_new = m.embeds[0]
                if _is_question(e_new) and _is_question(e_old):
                    if _norm(getattr(e_new, 'description', '')) == _norm(getattr(e_old, 'description', '')):
                        await _safe_delete(m); return
                p_new = _is_answer(e_new); p_old = _is_answer(e_old)
                if p_new and p_old and p_new == p_old:
                    await _safe_delete(m); return
        except Exception as e:
            log.debug('[qna-dedupe] history scan fail: %r', e)

    @commands.Cog.listener()
    async def on_message(self, m: 'discord.Message'):
        try:
            if not self.qid: return
            if getattr(getattr(m, 'channel', None), 'id', None) != self.qid: return
            if DELETE_NON_EMBED and (not getattr(m, 'embeds', None) or len(m.embeds) == 0):
                await _safe_delete(m); return
            if not getattr(m, 'embeds', None) or len(m.embeds) == 0: return
            if not getattr(getattr(m, 'author', None), 'bot', False): return
            e = m.embeds[0]
            if _is_question(e) or _is_answer(e):
                await self._scan_and_dedupe(m)
        except Exception as ex:
            log.warning('[qna-dedupe] fail: %r', ex)

async def setup(bot):
    await bot.add_cog(QnaDedupeAutolearn(bot))
