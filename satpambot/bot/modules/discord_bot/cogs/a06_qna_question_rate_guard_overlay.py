
from __future__ import annotations
import os, time, logging, json, urllib.request
from typing import Optional
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

def _env(k: str, d: Optional[str]=None) -> Optional[str]:
    v = os.getenv(k); return v if v not in (None,"") else d

def _qna_id() -> Optional[int]:
    try: v = int(_env("QNA_CHANNEL_ID","0") or "0"); return v or None
    except Exception: return None

def _cooldown() -> int:
    try: return int(_env("QNA_MIN_INTERVAL_SEC","180"))
    except Exception: return 180

def _pipe(cmds):
    base = _env("UPSTASH_REDIS_REST_URL"); tok = _env("UPSTASH_REDIS_REST_TOKEN")
    if not base or not tok: return None
    body = json.dumps(cmds).encode("utf-8")
    req = urllib.request.Request(f"{base}/pipeline", method="POST", data=body)
    req.add_header("Authorization", f"Bearer {tok}"); req.add_header("Content-Type","application/json")
    with urllib.request.urlopen(req, timeout=3.0) as r:
        return json.loads(r.read().decode("utf-8","ignore"))

def _is_question_embed(e: "discord.Embed") -> bool:
    title = (getattr(e, "title", "") or "").strip().lower()
    return title.startswith("question by leina")

class QnaQuestionRateGuardOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.qna = _qna_id()
        self.key = "qna:last_question_ts"
        self.cool = _cooldown()
        log.info("[qna-rate] cooldown=%ss channel=%s", self.cool, self.qna)

    @commands.Cog.listener()
    async def on_message(self, m: "discord.Message"):
        if not self.qna or getattr(getattr(m, "channel", None), "id", None) != self.qna:
            return
        if not getattr(m, "embeds", None): return
        if len(m.embeds)==0: return
        if not _is_question_embed(m.embeds[0]): return
        now = int(time.time())
        try:
            r = _pipe([["GET", self.key]])
            last = 0
            try:
                if r and r[0].get("result"):
                    last = int(str(r[0]["result"]).strip())
            except Exception:
                last = 0
            if last and now - last < self.cool:
                try:
                    await m.delete()
                    log.warning("[qna-rate] deleted question within cooldown (%ss)", self.cool)
                except Exception as e:
                    log.warning("[qna-rate] delete failed: %r", e)
                return
            _pipe([["SET", self.key, str(now)]])
        except Exception as e:
            log.debug("[qna-rate] storage err: %r", e)

async def setup(bot):
    await bot.add_cog(QnaQuestionRateGuardOverlay(bot))
