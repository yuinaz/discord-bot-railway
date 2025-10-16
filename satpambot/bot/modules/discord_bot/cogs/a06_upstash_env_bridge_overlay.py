import os
import logging
from discord.ext import commands

log = logging.getLogger(__name__)

def _copy_env(src: str, dst: str):
    val = os.getenv(src)
    if val and not os.getenv(dst):
        os.environ[dst] = val
        log.info("[upstash-overlay] mapped %s -> %s", src, dst)

def _ensure_upstash_env():
    # Accept common env var names from Render / Upstash dashboards and map
    # them to the ones expected by our XP bridge.
    _copy_env("UPSTASH_REDIS_REST_URL", "UPSTASH_REST_URL")
    _copy_env("UPSTASH_REDIS_REST_TOKEN", "UPSTASH_REST_TOKEN")
    _copy_env("UPSTASH_KV_REST_URL", "UPSTASH_REST_URL")
    _copy_env("UPSTASH_KV_REST_TOKEN", "UPSTASH_REST_TOKEN")
    _copy_env("UPSTASH_URL", "UPSTASH_REST_URL")
    _copy_env("UPSTASH_TOKEN", "UPSTASH_REST_TOKEN")

    # Ensure the feature flag is ON by default
    if not os.getenv("UPSTASH_ENABLE"):
        os.environ["UPSTASH_ENABLE"] = "1"
        log.info("[upstash-overlay] UPSTASH_ENABLE=1 (default)")

class UpstashEnvBridge(commands.Cog):
    """Early runtime overlay to normalize Upstash ENV before XP bridge loads."""
    def __init__(self, bot):
        self.bot = bot
        _ensure_upstash_env()
        url = os.getenv("UPSTASH_REST_URL")
        tok = os.getenv("UPSTASH_REST_TOKEN")
        url_preview = (url[:48] + "...") if url and len(url) > 51 else url
        log.info("[upstash-overlay] effective url=%s token=%s",
                 url_preview or "None",
                 "set" if tok else "missing")

async def setup(bot):
    # Load very early in the chain; filename prefix a06* keeps it early.
    await bot.add_cog(UpstashEnvBridge(bot))
