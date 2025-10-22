import os, json, logging, time
from datetime import datetime, timezone
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

def _now():
    return int(datetime.now(timezone.utc).timestamp())

def _ensure_quota_entry(entry):
    """Ensure quota entry is a dict with 'posts' list; never mutate None."""
    if not isinstance(entry, dict):
        return {"posts": []}
    posts = entry.get("posts")
    if not isinstance(posts, list):
        posts = []
    return {"posts": posts}

class NeuroAutolearnModeratedV2(commands.Cog):
    """
    Hotfix: never crash if internal quota/state is None or missing fields.
    This patch does NOT change config keys, formats, or behavior thresholds.
    """
    def __init__(self, bot):
        self.bot = bot
        self._quota = {}   # {channel_id: {"posts": [ts,...]}}
        self.period = max(60, int(os.getenv("AUTOLRN_SCAN_PERIOD_SEC","300") or "300"))
        self.task = self._scan.start()

    def cog_unload(self):
        try: self._scan.cancel()
        except Exception: pass

    def _may_post(self, channel_id: int) -> bool:
        """Sliding window quota: at most N posts per hour (configurable)."""
        try:
            limit = max(1, int(os.getenv("AUTOLRN_MAX_POSTS_PER_HOUR","6") or "6"))
        except Exception:
            limit = 6
        now = _now()
        entry = _ensure_quota_entry(self._quota.get(channel_id))
        # keep only last hour
        entry["posts"] = [t for t in entry.get("posts", []) if isinstance(t, (int, float)) and (now - int(t) < 3600)]
        ok = len(entry["posts"]) < limit
        if ok:
            entry["posts"].append(now)
        # write back
        self._quota[channel_id] = entry
        return ok

    async def _do_scan(self):
        # ... real scanning logic in your original file ...
        # This hotfix only ensures that _may_post() and internal state are safe.
        pass

    @tasks.loop(seconds=30)
    async def _scan(self):
        now = _now()
        if now % self.period != 0:
            return
        try:
            await self._do_scan()
        except Exception as e:
            log.error("autolearn scan error", exc_info=True)

    @_scan.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(NeuroAutolearnModeratedV2(bot))
