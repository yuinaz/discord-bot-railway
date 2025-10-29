from __future__ import annotations
import os, re, json, logging, urllib.request, time, asyncio
from typing import Optional, List, Tuple
import discord
from discord.ext import commands
log = logging.getLogger(__name__)
def _env(k, d=None): v=os.getenv(k); return v if v not in (None,"") else d
def _ids(val: Optional[str]) -> List[int]:
    if not val: return []
    out=[]; 
    for part in re.split(r"[\s,]+", str(val)):
        part=part.strip(); 
        if not part: continue
        try: out.append(int(part))
        except: pass
    return out
def _pipe(cmds):
    b=_env("UPSTASH_REDIS_REST_URL"); t=_env("UPSTASH_REDIS_REST_TOKEN")
    if not b or not t: return None
    body=json.dumps(cmds).encode("utf-8")
    req=urllib.request.Request(f"{b}/pipeline", method="POST", data=body)
    req.add_header("Authorization", f"Bearer {t}"); req.add_header("Content-Type","application/json")
    with urllib.request.urlopen(req, timeout=3.5) as r: return json.loads(r.read().decode("utf-8","ignore"))
def _order() -> List[str]:
    raw=_env("QNA_PROVIDER_ORDER","gemini,groq") or "gemini,groq"
    return [x.strip().lower() for x in re.split(r"[\s,]+", raw) if x.strip()]
def _has_gemini() -> bool:
    for k in ("GEMINI_API_KEY","GOOGLE_API_KEY","GOOGLE_GENAI_API_KEY","GOOGLE_AI_API_KEY"):
        if os.getenv(k): return True
    return False
def _has_groq() -> bool: return bool(os.getenv("GROQ_API_KEY"))
async def _llm(topic: str) -> Tuple[str,str]:
    try:
        from satpambot.bot.providers.llm import LLM; llm = LLM()
    except Exception as e:
        log.warning("[qna-public] LLM provider missing: %r", e); return ("fallback","Maaf, LLM belum aktif.")
    order=_order() or ["gemini","groq"]
    for p in order:
        try:
            if p.startswith("gem") and _has_gemini():
                ans=await llm.chat_gemini(prompt=topic, messages=None, system_prompt=None, temperature=0.3, max_tokens=None)
                if ans: return ("gemini", ans)
            if (p.startswith("groq") or p.startswith("llama") or p.startswith("mixtral")) and _has_groq():
                ans=await llm.chat_groq(prompt=topic, messages=None, system_prompt=None, temperature=0.3, max_tokens=None)
                if ans: return ("groq", ans)
        except Exception as e:
            log.warning("[qna-public] provider %s failed: %r", p, e); await asyncio.sleep(0.1)
    try:
        ans=await llm.chat(prompt=topic, messages=None, system_prompt=None, temperature=0.3, max_tokens=None)
        if ans: return ("fallback", ans)
    except Exception as e:
        log.warning("[qna-public] llm.chat fallback failed: %r", e)
    return ("fallback","Maaf, provider QnA sedang tidak tersedia sekarang.")
def _cool_key(uid:int, cid:int) -> str: return f"qna:pub:cool:{uid}:{cid}"
def _cool_sec() -> int:
    try: return int(_env("QNA_PUBLIC_COOLDOWN_SEC","60"))
    except: return 60
def _award() -> int:
    try: return int(_env("QNA_PUBLIC_ANSWER_XP","0"))
    except: return 0
class QnaPublicMentionReplyOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot=bot
        self.enabled = (_env("QNA_PUBLIC_ENABLE","1") or "1") not in ("0","false","False")
        self.require_mention = (_env("QNA_PUBLIC_REQUIRE_MENTION","1") or "1") not in ("0","false","False")
        self.allow = set(_ids(_env("QNA_PUBLIC_ALLOWLIST","")))
        log.info("[qna-public] enable=%s require_mention=%s allow=%s", self.enabled, self.require_mention, sorted(self.allow))
    def _ok(self, cid: Optional[int]) -> bool:
        if not self.enabled or not cid: return False
        if not self.allow: return True
        return cid in self.allow
    @commands.Cog.listener()
    async def on_message(self, m: "discord.Message"):
        ch=getattr(m,"channel",None); cid=getattr(ch,"id",None)
        if not self._ok(cid): return
        if self.require_mention:
            me = getattr(m.guild.me,"id",None) if getattr(m,"guild",None) else getattr(getattr(self.bot,"user",None),"id",None)
            mentioned=False
            try:
                for u in (getattr(m,"mentions",[]) or []):
                    if getattr(u,"id",None)==me: mentioned=True; break
            except Exception: mentioned=False
            if not mentioned: return
        uid = getattr(getattr(m, "author", None), "id", None) or 0
        key=_cool_key(int(uid), int(cid or 0)); cool=_cool_sec()
        try:
            r=_pipe([["GET", key]])
            if r and r[0].get("result"): return
            _pipe([["SETEX", key, str(cool), "1"]])
        except Exception: pass
        content=(getattr(m,"content","") or "")
        topic=re.sub(r"<@!?(\d+)>","",content).strip()
        if not topic: return
        prov, text = await _llm(topic)
        try:
            emb=discord.Embed(title=f"Answer by {prov.capitalize()}", description=text, colour=getattr(discord.Colour,"blue")().value)
            await m.reply(embed=emb, mention_author=False)
        except Exception:
            try: await ch.send(text or "Maaf, gagal memproses pertanyaan.")
            except: pass
        amt=_award()
        if amt:
            try: self.bot.dispatch("xp_add", uid, amt, "public_mention_qna")
            except Exception: pass
async def setup(bot): await bot.add_cog(QnaPublicMentionReplyOverlay(bot))