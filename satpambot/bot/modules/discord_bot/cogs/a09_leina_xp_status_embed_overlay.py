
from __future__ import annotations
import os, json, time, asyncio, logging, math, urllib.request, urllib.parse
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

# --- Safe helpers ------------------------------------------------------------

def _intenv(k: str, d: int) -> int:
    try: return int(os.getenv(k, str(d)))
    except Exception: return d

def _strenv(k: str, d: str) -> str:
    v = os.getenv(k)
    return v if v not in (None, "") else d

async def _compat_compute() -> Dict[str, Any]:
    """Try to use compat_learning_status.compute(); fall back to empty structure."""
    try:
        from satpambot.bot.modules.discord_bot.helpers.compat_learning_status import compute as _compute
        data = await _compute()
        if isinstance(data, dict):
            return data
    except Exception as e:
        log.debug("[xp-status] compat compute unavailable: %r", e)
    return {
        "label": "SMP",
        "percent": 0.0,
        "remaining": 0,
        "senior_total": 0,
        "stage": {"start_total": 0, "required": 0, "current": 0},
    }

async def _get_total_from_upstash(key: str) -> Optional[int]:
    """Use UpstashClient.get_raw when available; fall back to REST."""
    # Prefer native client (with local fallback integration, if present)
    try:
        from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
        cli = UpstashClient()
        raw = await cli.get_raw(key)
        if raw is None:
            return None
        s = str(raw)
        if s.isdigit():
            return int(s)
        try:
            obj = json.loads(s)
            # common shapes: {"result": "123"} or {"overall": 123}
            if "overall" in obj:
                return int(obj["overall"])
            if "result" in obj and str(obj["result"]).strip().isdigit():
                return int(obj["result"])
        except Exception:
            pass
        # last attempt: int()
        return int(float(s))
    except Exception as e:
        log.debug("[xp-status] UpstashClient path failed: %r", e)

    # Fallback: direct REST
    try:
        base = (os.getenv("UPSTASH_REDIS_REST_URL") or "").rstrip("/")
        tok  = os.getenv("UPSTASH_REDIS_REST_TOKEN") or ""
        if not base or not tok:
            return None
        req = urllib.request.Request(base + "/get/" + urllib.parse.quote(key, safe=""),
                                     headers={"Authorization": f"Bearer {tok}"})
        with urllib.request.urlopen(req, timeout=10) as r:
            j = json.loads(r.read().decode())
        res = j.get("result")
        if isinstance(res, (int, float)):
            return int(res)
        s = str(res)
        if s.isdigit():
            return int(s)
        return int(float(s))
    except Exception as e:
        log.debug("[xp-status] REST path failed: %r", e)
        return None

def _recompute_from_stage(total: int, stage: Dict[str, Any]) -> Dict[str, Any]:
    """Recompute percent/remaining/current using stage boundaries when possible."""
    start_total = int(stage.get("start_total") or 0)
    required    = int(stage.get("required") or 0)
    if required <= start_total:
        # avoid div/0
        pct = 0.0
        remaining = max(0, required - total)
        current = max(start_total, min(total, required))
    else:
        span = max(1, required - start_total)
        current = max(start_total, min(total, required))
        pct = max(0.0, min(100.0, (current - start_total) * 100.0 / span))
        remaining = max(0, required - total)
    return {"percent": pct, "remaining": remaining, "current": current,
            "start_total": start_total, "required": required}

# --- The Cog -----------------------------------------------------------------

class LeinaXpStatusOverlay(commands.Cog):
    """Keep a single '[leina:xp_status]' message updated every N seconds.

    ENV:
      LEINA_XP_STATUS_CHANNEL_ID   (required-ish; fallback to LOG_CHANNEL_ID)
      LEINA_XP_STATUS_MESSAGE_ID   (optional fixed message id)
      LEINA_XP_STATUS_PERIOD_SEC   (default 1200 = 20 minutes)
      LEINA_XP_STATUS_MARKER       (default 'leina:xp_status')
      XP_SENIOR_KEY                (default 'xp:bot:senior_total')
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_id = _intenv("LEINA_XP_STATUS_CHANNEL_ID", _intenv("LOG_CHANNEL_ID", 0))
        self.message_id = _intenv("LEINA_XP_STATUS_MESSAGE_ID", 0) or None
        self.period = max(60, _intenv("LEINA_XP_STATUS_PERIOD_SEC", 1200))
        self.marker = _strenv("LEINA_XP_STATUS_MARKER", "leina:xp_status")
        self.xp_key = _strenv("XP_SENIOR_KEY", "xp:bot:senior_total")
        self._task: Optional[asyncio.Task] = asyncio.create_task(self._runner())

    def cog_unload(self):
        try:
            if self._task:
                self._task.cancel()
        except Exception:
            pass

    async def _render_embed(self) -> discord.Embed:
        data = await _compat_compute()

        # Override totals from Upstash (aware of local fallback) when possible
        try:
            total = await _get_total_from_upstash(self.xp_key)
        except Exception as e:
            log.debug("[xp-status] total fetch error: %r", e)
            total = None

        if total is not None:
            stage = data.get("stage") or {}
            rec = _recompute_from_stage(int(total), stage)
            data["percent"] = rec["percent"]
            data["remaining"] = rec["remaining"]
            data["senior_total"] = int(total)
            data["stage"] = {
                "start_total": rec["start_total"],
                "required": rec["required"],
                "current": rec["current"],
            }

        label = str(data.get("label") or "SMP")
        pct   = float(data.get("percent") or 0.0)
        rem   = int(data.get("remaining") or 0)
        total = int(data.get("senior_total") or 0)
        st    = data.get("stage") or {}
        start_total = int(st.get("start_total") or 0)
        required    = int(st.get("required") or 0)
        current     = int(st.get("current") or 0)

        e = discord.Embed(
            title="Leina Progress",
            description=f"**{label}** • **{pct:.1f}%**  |  total: **{total:,}** XP",
            color=0x3BA55D,
        )
        e.add_field(name="Stage window", value=f"{start_total:,} → {required:,}", inline=True)
        e.add_field(name="Current", value=f"{current:,}", inline=True)
        e.add_field(name="Remaining", value=f"{rem:,}", inline=True)
        e.set_footer(text=self.marker + " • updated")
        e.timestamp = datetime.now(timezone.utc)
        return e

    async def _upsert(self, embed: discord.Embed) -> Optional[int]:
        # Prefer EmbedScribe if present
        try:
            from satpambot.bot.modules.discord_bot.helpers.embed_scribe import EmbedScribe
            mid = await EmbedScribe.upsert(
                self.bot,
                self.channel_id,
                content=self.marker,
                embed=embed,
                marker=self.marker,
                pin=True,
                message_id=self.message_id,
            )
            return mid or self.message_id
        except Exception as e:
            log.debug("[xp-status] scribe upsert failed: %r", e)

        # Fallback: raw edit (will not pin automatically)
        try:
            ch = self.bot.get_channel(self.channel_id) or await self.bot.fetch_channel(self.channel_id)
            if self.message_id:
                msg = await ch.fetch_message(self.message_id)
                await msg.edit(content=self.marker, embed=embed)
                return self.message_id
            # Try find existing marker message
            async for msg in ch.history(limit=50):
                if self.marker in (msg.content or ""):
                    await msg.edit(content=self.marker, embed=embed)
                    return msg.id
            # Post new one
            m = await ch.send(self.marker, embed=embed)
            return m.id
        except Exception as e:
            log.warning("[xp-status] raw upsert failed: %r", e)
            return None

    async def _runner(self):
        await self.bot.wait_until_ready()
        if not self.channel_id:
            log.warning("[xp-status] channel id missing; set LEINA_XP_STATUS_CHANNEL_ID or LOG_CHANNEL_ID")
            return
        last = 0.0
        while True:
            try:
                now = time.time()
                if now - last >= self.period:
                    embed = await self._render_embed()
                    mid = await self._upsert(embed)
                    if mid and not self.message_id:
                        self.message_id = mid
                    last = now
                    log.info("[xp-status] updated (msg_id=%s)", mid or self.message_id)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.warning("[xp-status] update failed: %r", e)
            await asyncio.sleep(5)

async def setup(bot: commands.Bot):
    await bot.add_cog(LeinaXpStatusOverlay(bot))
