
import os, logging, importlib
from discord.ext import commands, tasks
try:
    import httpx
except Exception:
    httpx = None

log = logging.getLogger(__name__)

UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")
PHASE_KEY = os.getenv("LEARNING_PHASE_KEY","learning:phase")
TK_KEY = os.getenv("TK_XP_KEY","xp:bot:tk_total")
SR_KEY = os.getenv("SENIOR_XP_KEY","xp:bot:senior_total")
DEFAULT_PHASE = os.getenv("LEARNING_PHASE_DEFAULT","tk")
REFRESH_MIN = int(os.getenv("XP_OFFSET_REFRESH_MIN","10"))

async def _get(client, key):
    r = await client.get(f"{UPSTASH_URL}/get/{key}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"})
    if r.status_code == 200:
        return (r.json() or {}).get("result")

class PassiveLearningTotalOffset(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._client = httpx.AsyncClient(timeout=8.0) if httpx else None
        self._offset = 0
        self.refresh.start()

    def _current_phase(self):
        st = getattr(self.bot, "_xp_state", {}) if hasattr(self.bot, "_xp_state") else {}
        return (st.get("phase") or DEFAULT_PHASE).lower()

    @tasks.loop(minutes=REFRESH_MIN)
    async def refresh(self):
        if not (UPSTASH_URL and UPSTASH_TOKEN and self._client):
            return
        try:
            phase = await _get(self._client, PHASE_KEY) or self._current_phase()
            if str(phase).lower().startswith("senior"):
                base = await _get(self._client, SR_KEY)
            else:
                base = await _get(self._client, TK_KEY)
            self._offset = int(base or 0)
            log.info("[passive-total-offset] phase=%s base_offset=%s", phase, self._offset)
        except Exception as e:
            log.warning("[passive-total-offset] refresh fail: %r", e)

    @refresh.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            m = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.learning_passive_observer")
        except Exception as e:
            log.debug("[passive-total-offset] import fail: %r", e); return
        fn = getattr(m, "compute_label_from_group", None)
        if callable(fn) and not getattr(fn, "__offset_patched__", False):
            def wrapped(total_xp, ladder_map, phase=None):
                total = int(total_xp or 0) + int(getattr(self, "_offset", 0))
                return fn(total, ladder_map, phase=phase)
            wrapped.__offset_patched__ = True
            m.compute_label_from_group = wrapped
            log.info("[passive-total-offset] hooked compute_label_from_group (+offset)")

async def setup(bot):
    await bot.add_cog(PassiveLearningTotalOffset(bot))
