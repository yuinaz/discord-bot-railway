# a08_xp_upstash_exact_keys_overlay.py
# Fix TypeError: "cogs must derive from Cog" by wrapping logic into a Cog class.
# Also accept flexible event signatures for on_satpam_xp and on_satpam_xp_set_global.
from discord.ext import commands
import json, os, numbers

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

    @commands.Cog.listener()
    async def on_satpam_xp_set_global(self, *args, **kwargs):
        # Accept state via positional or keyword.
        # Expected: a single dict arg or state=<dict>
        state = None
        if args:
            state = args[0]
        if state is None:
            state = kwargs.get("state")
        # We don't need to enforce anything here; this is a normalization hook.
        return

    @commands.Cog.listener()
    async def on_satpam_xp(self, *args, **kwargs):
        # Different emitters may pass (user_id, delta, reason, message, channel, ctx, ...)
        # or a single payload dict. We keep it as a safe no-op to avoid signature errors.
        return

async def setup(bot):
    await bot.add_cog(UpstashExactKeysOverlay(bot))
