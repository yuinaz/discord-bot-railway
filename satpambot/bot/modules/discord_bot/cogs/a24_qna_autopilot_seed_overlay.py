
from __future__ import annotations
import os, json, random, asyncio, logging, urllib.request, urllib.parse
from pathlib import Path
from typing import List
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

def _env_int(k: str, default: int) -> int:
    try:
        return int(os.getenv(k, str(default)))
    except Exception:
        return default

def _cfg_qna_channel_id() -> int:
    for k in ("QNA_CHANNEL_ID", "LEARNING_QNA_CHANNEL_ID"):
        v = os.getenv(k)
        if v and str(v).isdigit():
            return int(v)
    return 0

class _UpstashLite:
    def __init__(self):
        self.base = (os.getenv("UPSTASH_REDIS_REST_URL") or "").rstrip("/")
        self.tok  = os.getenv("UPSTASH_REDIS_REST_TOKEN") or ""
        self.enabled = bool(self.base and self.tok)
    def _req(self, path: str):
        if not self.enabled: return None
        req = urllib.request.Request(self.base + path, headers={"Authorization": f"Bearer {self.tok}"})
        with urllib.request.urlopen(req, timeout=10) as r:
            s = r.read().decode()
            import json as _j
            try: return _j.loads(s)
            except Exception: return {"result": s}
    async def get(self, key: str):
        from urllib.parse import quote
        r = self._req("/get/" + quote(key, safe=""))
        return None if r is None else r.get("result")
    async def setex(self, key: str, seconds: int, val: str = "1"):
        from urllib.parse import quote
        self._req("/set/" + quote(key, safe="") + "/" + quote(val, safe=""))
        self._req("/expire/" + quote(key, safe="") + "/" + str(int(seconds)))
        return True
    async def delete(self, key: str):
        from urllib.parse import quote
        self._req("/del/" + quote(key, safe=""))
        return True

def _topics_path() -> Path:
    cands = [Path("data/config/qna_topics.json"), Path("satpambot/data/config/qna_topics.json")]
    for p in cands:
        if p.exists(): return p
    return cands[0]

def _load_questions() -> List[str]:
    p = _topics_path()
    try:
        j = json.loads(p.read_text("utf-8"))
        if isinstance(j, dict) and "topics" in j:
            return [str(x) for x in j["topics"] if str(x).strip()]
        if isinstance(j, list):
            return [str(x) for x in j if str(x).strip()]
    except Exception as e:
        log.warning("[qna-autopilot] failed to load %s: %r", p, e)
    return ["Apa manfaat olahraga rutin bagi kesehatan?"]

def _build_question_embed(q: str) -> discord.Embed:
    return discord.Embed(title="Question by Leina", description=q)

WAIT_KEY = "qna:waiting"
LAST_Q_KEY = "qna:last_question_id"

class QnaAutopilotSeedOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_id = _cfg_qna_channel_id()
        self.interval = _env_int("QNA_SEED_INTERVAL_SEC", 180)
        self.answer_timeout = _env_int("QNA_ANSWER_TIMEOUT_SEC", 180)
        self.enabled = bool(int(os.getenv("QNA_AUTOPILOT_ENABLE", os.getenv("QNA_ENABLE","1") or "1")))
        self._qs = _load_questions()
        self.us = _UpstashLite()
        self._task = asyncio.create_task(self._loop())

    async def _emit_one(self):
        if not self.channel_id or not self.enabled:
            return
        # 1 QUESTION → 1 ANSWER: jangan seed kalau masih menunggu jawaban
        if self.us.enabled and await self.us.get(WAIT_KEY) is not None:
            return
        ch = self.bot.get_channel(self.channel_id) or await self.bot.fetch_channel(self.channel_id)
        q = random.choice(self._qs)
        try:
            msg = await ch.send(embed=_build_question_embed(q))
            # set waiting gate with timeout
            if self.us.enabled:
                await self.us.setex(WAIT_KEY, max(60, self.answer_timeout), "1")
                await self.us.setex(LAST_Q_KEY, max(24*3600, self.answer_timeout), str(getattr(msg, "id", "")))
            log.info("[qna-autopilot] seeded Q and set waiting gate")
        except Exception as e:
            log.warning("[qna-autopilot] send failed: %r", e)

    async def _loop(self):
        await self.bot.wait_until_ready()
        while not getattr(self.bot, "is_closed", lambda: False)():
            try:
                await self._emit_one()
            except Exception:
                pass
            await asyncio.sleep(max(60, int(self.interval)))

    async def cog_unload(self):
        try: self._task.cancel()
        except Exception: pass

async def setup(bot: commands.Bot):
    await bot.add_cog(QnaAutopilotSeedOverlay(bot))
