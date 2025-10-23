
# patched a06_autolearn_qna_answer_overlay.py
from discord.ext import commands
import logging, asyncio, json, os
from discord.ext import tasks
from satpambot.bot.utils.json import tolerant_loads, tolerant_dumps

LOG = logging.getLogger(__name__)

def _d(d):
    return d if isinstance(d, dict) else {}

def _s(v, default=""):
    try:
        return str(v)
    except Exception:
        return default

class AutoLearnQnAAnswerOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._task = self._loop.start()

    def cog_unload(self):
        try: self._task.cancel()
        except Exception: pass

    @tasks.loop(minutes=2)
    async def _loop(self):
        try:
            await self._tick_once()
        except Exception as e:
            LOG.warning("[autolearn] error: %r", e)

    @_loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    async def _tick_once(self):
        # retrieve pending Qs from a store (best-effort); tolerate missing/None
        store = getattr(self.bot, "autolearn_store", None)
        if not isinstance(store, dict):
            return
        q = store.get("pending")
        if not isinstance(q, dict):
            return
        text = _s(q.get("text","")).strip()
        if not text:
            return

        # ask provider (best-effort)
        ans = await self._ask_llm(text)
        if not ans:
            return

        # xp award (best-effort)
        xp = int(os.getenv("QNA_XP_AWARD", "5") or "5")
        try:
            award = getattr(self.bot, "satpam_xp", None) or getattr(self.bot, "xp_add", None) or getattr(self.bot, "xp_award", None)
            if callable(award):
                await award(q.get("author_id"), xp, "qna:auto-learn")
        except Exception:
            pass

        # mark answered to avoid duplication
        q["answered"] = True

    async def _ask_llm(self, prompt: str):
        # try bot.llm_ask if available
        fn = getattr(self.bot, "llm_ask", None)
        if callable(fn):
            try:
                resp = await fn(prompt, provider_order=["groq","gemini"])
                data = _d(resp)  # ensure dict
                return data.get("answer") or data.get("text") or _s(resp, "")
            except Exception:
                pass
        # fallback: Groq/Gemini raw calls if configured (omitted here; rely on existing cogs)
        return None
async def setup(bot):
    await bot.add_cog(AutoLearnQnAAnswerOverlay(bot))