
# -*- coding: utf-8 -*-
import os, time, hashlib, logging
from discord.ext import commands
log=logging.getLogger(__name__)
def _norm(s): return " ".join((s or "").strip().split()).lower()
def _h(s): 
    import hashlib; return hashlib.sha256(s.encode("utf-8")).hexdigest()
class Dedup(commands.Cog):
    def __init__(self,bot): self.bot=bot; self.ttl=int(os.getenv("QNA_DEDUP_WINDOW_SEC","90")); self._mem={}
    @commands.Cog.listener()
    async def on_message(self,m):
        if not getattr(m.author,"bot",False): return
        if not m.embeds: return
        e=m.embeds[0]; title=(getattr(e,"title","") or "").strip().lower()
        if title!="question by leina": return
        desc=(getattr(e,"description","") or "").strip()
        q=_norm(desc); 
        if not q: return
        key=str(getattr(getattr(m,"channel",None),"id",0)); h=_h(q)
        now=time.time(); prev=self._mem.get(key)
        if prev and prev[0]==h and (now-prev[1])<self.ttl:
            try: await m.delete(); log.info("[qna-dedup] delete dup in %s", key)
            except Exception: pass
        else:
            self._mem[key]=(h,now)
async def setup(bot): await bot.add_cog(Dedup(bot))
