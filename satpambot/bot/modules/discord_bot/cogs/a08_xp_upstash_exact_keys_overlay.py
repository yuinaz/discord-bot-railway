# a08_xp_upstash_exact_keys_overlay.py
# Fix TypeError: "cogs must derive from Cog" by wrapping logic into a Cog class.
from discord.ext import commands
import json, os

# cfg() helper
try:
    from satpambot.config.runtime import cfg
    def _cfg(k, default=None):
        try:
            v = cfg(k)
            return default if v in (None, "") else v
        except Exception:
            return os.getenv(k, default)
except Exception:
    def _cfg(k, default=None):
        return os.getenv(k, default)

_DEFAULT_KEYS = {"senior_total":"xp:bot:senior_total","tk_total":"xp:bottk_total","phase":"learning:phase"}
try:
    XP_KEYS = json.loads(_cfg("XP_UPSTASH_BOT_KEYS_JSON", json.dumps(_DEFAULT_KEYS)))
except Exception:
    XP_KEYS = _DEFAULT_KEYS

class UpstashExactKeysOverlay(commands.Cog):
    """
    Ensure we always use the exact legacy key names in Upstash to avoid creating new keys.
    Hook points are provided but left no-op, because the writing is already handled by the sink overlay.
    """
    def __init__(self, bot):
        self.bot = bot

    # Event from PreferUpstashBootstrap to set absolute state; hook if you need custom mirroring.
    @commands.Cog.listener("on_satpam_xp_set_global")
    async def on_set_global(self, state):
        # Example: mirror/validate keys or emit metrics. Keep no-op if not needed.
        # state = {"senior_total": int, "tk_total": int, "phase": str}
        return

    # If your pipeline emits granular XP events and you want to sanity-check the keys, do it here.
    @commands.Cog.listener("on_satpam_xp")
    async def on_satpam_xp(self, payload):
        # payload example depends on your system; keep as a safe no-op.
        return

async def setup(bot):
    await bot.add_cog(UpstashExactKeysOverlay(bot))
