
"""
a00_upstash_env_bridge.py
--------------------------------
Early overlay to normalize Upstash env variable names so the rest of the
bot (XP bridge, memory) can detect and use Upstash on Render.

Render commonly exposes:
  - UPSTASH_REDIS_REST_URL
  - UPSTASH_REDIS_REST_TOKEN

Some modules expect:
  - UPSTASH_REST_URL
  - UPSTASH_REST_TOKEN

This overlay maps any of the known variants toUPSTASH_REST_URL/TOKEN and
sets UPSTASH_ENABLE=1 when creds are present.
"""
import os
import logging

log = logging.getLogger(__name__)

def _first(*names: str) -> str | None:
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return None

# Normalize on import (very early)
url = _first("UPSTASH_REST_URL", "UPSTASH_REDIS_REST_URL", "UPSTASH_KV_REST_URL")
token = _first("UPSTASH_REST_TOKEN", "UPSTASH_REDIS_REST_TOKEN", "UPSTASH_KV_REST_TOKEN")

# Populate canonical keys if missing
if not os.environ.get("UPSTASH_REST_URL") and url:
    os.environ["UPSTASH_REST_URL"] = url
if not os.environ.get("UPSTASH_REST_TOKEN") and token:
    os.environ["UPSTASH_REST_TOKEN"] = token

# Enable Upstash if creds exist
if os.environ.get("UPSTASH_REST_URL") and os.environ.get("UPSTASH_REST_TOKEN"):
    os.environ.setdefault("UPSTASH_ENABLE", "1")

def _safe(v: str | None, maxlen: int = 48) -> str:
    if not v:
        return "missing"
    return (v[:maxlen] + "…") if len(v) > maxlen else v

log.info(
    "[upstash-overlay] enable=%s url=%s token=%s",
    os.environ.get("UPSTASH_ENABLE", "0"),
    _safe(os.environ.get("UPSTASH_REST_URL")),
    "set" if os.environ.get("UPSTASH_REST_TOKEN") else "missing",
)

# Minimal, no-op cog (kept for consistent loader behavior)
class _UpstashEnvBridge:
    def __init__(self, bot):  # pragma: no cover
        self.bot = bot

async def setup(bot):  # pragma: no cover
    _UpstashEnvBridge(bot)
