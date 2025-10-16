import asyncio
import json
import logging
from typing import Any, Dict, Optional, Tuple

from .a06_upstash_kv_client import UpstashClient, json_loads_maybe_twice, iso_now

log = logging.getLogger(__name__)


def _coerce_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _parse_xp_event(*args, **kwargs) -> Tuple[Optional[int], int, Optional[str]]:
    """
    Accepts many shapes:
      on_xp_add(user_id, amount, reason=None)
      on_xp_add({"user_id":..., "amount":..., "reason":...})
      on_xp_add(user_id=..., amount=..., reason=...)
    Returns: (user_id, amount, reason) — user_id may be None if unknown.
    """
    user_id = None
    amount = 0
    reason = None

    if args:
        if len(args) == 1 and isinstance(args[0], dict):
            d = args[0]
            user_id = d.get("user_id")
            amount = _coerce_int(d.get("amount"), 0)
            reason = d.get("reason")
        elif len(args) >= 2:
            user_id = args[0]
            amount = _coerce_int(args[1], 0)
            if len(args) >= 3:
                reason = args[2]
    else:
        # kwargs path
        if "payload" in kwargs and isinstance(kwargs["payload"], dict):
            d = kwargs["payload"]
            user_id = d.get("user_id")
            amount = _coerce_int(d.get("amount"), 0)
            reason = d.get("reason")
        else:
            user_id = kwargs.get("user_id")
            amount = _coerce_int(kwargs.get("amount"), 0)
            reason = kwargs.get("reason")

    try:
        if user_id is not None:
            user_id = int(user_id)
    except Exception:
        # leave as-is if cannot coerce cleanly
        pass

    return user_id, amount, reason


class XPUpstashExactKeysOverlay:
    """
    Persist XP strictly into these Upstash keys:
      - learning:phase          -> {"phase":"senior" | "tk"}
      - xp:bot:senior_total     -> {"senior_total_xp": <int>}
      - xp:bottk_total          -> {"tk_total_xp": <int>, "levels": {...}, "last_update": "<iso>"}

    Rules:
      - NEVER create new keys. If a key is missing, we log and skip rather than creating it.
      - Continue values (no reset). We read, add deltas, write back same shape.
      - Low-write mode: we batch increments and flush every ~10s or when buffers are big.
    """

    FLUSH_INTERVAL = 10.0
    MAX_BUFFER = 50

    def __init__(self, bot):
        self.bot = bot
        self.client = UpstashClient()
        self._buf_tk = 0
        self._buf_senior = 0
        self._phase_cache: Optional[str] = None
        self._task: Optional[asyncio.Task] = None

        # In smoke tests DummyBot doesn't have .loop; guard background task
        loop = getattr(bot, "loop", None)
        if loop and not getattr(bot, "_satpam_disable_tasks", False):
            self._task = loop.create_task(self._flusher_task())
        else:
            log.info("[xp-upstash] background flusher not started (no loop/smoke)")

    async def cog_unload(self):
        if self._task:
            self._task.cancel()

    # ---- Utilities ---------------------------------------------------------

    async def _get_phase(self) -> str:
        """Return 'senior' or 'tk' (default to 'tk' if not found/invalid)."""
        if not self.client.ready():
            return "tk"
        raw = await self.client.get_raw("learning:phase")
        data = json_loads_maybe_twice(raw)
        if isinstance(data, dict) and data.get("phase") in ("senior", "tk"):
            return data["phase"]
        # Accept plain string "senior"/"tk"
        if isinstance(data, str) and data in ("senior", "tk"):
            return data
        return "tk"

    async def _load_totals(self) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Load JSON for (senior_key, tk_key). Return None for missing."""
        raw_senior = await self.client.get_raw("xp:bot:senior_total")
        raw_tk = await self.client.get_raw("xp:bottk_total")
        js_senior = json_loads_maybe_twice(raw_senior)
        js_tk = json_loads_maybe_twice(raw_tk)
        return js_senior if isinstance(js_senior, dict) else None, js_tk if isinstance(js_tk, dict) else None

    async def _flush_once(self) -> None:
        if not self.client.ready():
            return
        if self._buf_senior == 0 and self._buf_tk == 0:
            return

        js_senior, js_tk = await self._load_totals()

        cmds = []
        wrote = False

        if self._buf_senior:
            if js_senior is None or "senior_total_xp" not in js_senior:
                log.warning("[xp-upstash] skip senior flush: key missing or invalid shape")
            else:
                js_senior["senior_total_xp"] = _coerce_int(js_senior.get("senior_total_xp"), 0) + self._buf_senior
                cmds.append(["SET", "xp:bot:senior_total", json.dumps(js_senior, ensure_ascii=False)])
                wrote = True

        if self._buf_tk:
            if js_tk is None or "tk_total_xp" not in js_tk:
                log.warning("[xp-upstash] skip TK flush: key missing or invalid shape")
            else:
                js_tk["tk_total_xp"] = _coerce_int(js_tk.get("tk_total_xp"), 0) + self._buf_tk
                js_tk["last_update"] = iso_now()
                cmds.append(["SET", "xp:bottk_total", json.dumps(js_tk, ensure_ascii=False)])
                wrote = True

        if wrote:
            ok = await self.client.pipeline(cmds)
            if ok:
                log.info("[xp-upstash] flushed +senior=%s +tk=%s", self._buf_senior, self._buf_tk)
                self._buf_senior = 0
                self._buf_tk = 0
            else:
                log.warning("[xp-upstash] pipeline write failed (kept buffers)")

    async def _flusher_task(self):
        await asyncio.sleep(3.0)
        log.info("[xp-upstash] using Upstash at %s", self.client.url or "(unset)")
        while True:
            try:
                await self._flush_once()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.exception("[xp-upstash] flusher error: %s", e)
            await asyncio.sleep(self.FLUSH_INTERVAL)

    async def _route_and_buffer(self, amount: int):
        try:
            phase = await self._get_phase()
        except Exception:
            phase = "tk"
        if phase == "senior":
            self._buf_senior += amount
        else:
            self._buf_tk += amount

        if (self._buf_senior + self._buf_tk) >= self.MAX_BUFFER:
            await self._flush_once()

    # ---- Event listeners ---------------------------------------------------

    async def on_ready(self):
        # Log preload state briefly (do not modify anything)
        if not self.client.ready():
            log.warning("[xp-upstash] Upstash client not ready (missing env or httpx)")
            return
        js_senior, js_tk = await self._load_totals()
        log.info(
            "[xp-upstash] preload senior=%s tk=%s",
            (js_senior or {}).get("senior_total_xp"),
            (js_tk or {}).get("tk_total_xp"),
        )

    async def on_xp_add(self, *args, **kwargs):
        _uid, amount, _reason = _parse_xp_event(*args, **kwargs)
        if amount <= 0:
            return
        await self._route_and_buffer(amount)

    async def on_satpam_xp(self, *args, **kwargs):
        _uid, amount, _reason = _parse_xp_event(*args, **kwargs)
        if amount <= 0:
            return
        await self._route_and_buffer(amount)

    async def on_xp_award(self, *args, **kwargs):
        _uid, amount, _reason = _parse_xp_event(*args, **kwargs)
        if amount <= 0:
            return
        await self._route_and_buffer(amount)


async def setup(bot):
    """
    Cog entrypoint (Discord.py 2.x style). Safe in smoke: no background task if DummyBot.
    """
    try:
        await bot.add_cog(XPUpstashExactKeysOverlay(bot))
        log.info("[xp-upstash] overlay loaded (exact keys mode)")
    except Exception as e:
        log.warning("[xp-upstash] setup failed: %r", e)
