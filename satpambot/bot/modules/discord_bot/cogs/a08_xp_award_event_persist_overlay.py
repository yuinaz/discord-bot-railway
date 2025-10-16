
import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, Optional

from discord.ext import commands

log = logging.getLogger(__name__)

_STORE_PATH = os.environ.get(
    "XP_STORE_FILE",
    "satpambot/bot/data/xp_store.json"
)


def _now_ts() -> int:
    try:
        return int(time.time())
    except Exception:
        return int(time.time())


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)  # type: ignore[arg-type]
    except Exception:
        return default


async def _read_json(path: str) -> Dict[str, Any]:
    def _read() -> Dict[str, Any]:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return await asyncio.to_thread(_read)


async def _write_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    dumped = json.dumps(data, ensure_ascii=False, indent=2)
    def _write() -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(dumped)
    await asyncio.to_thread(_write)


def _ensure_store_shape(store: Dict[str, Any]) -> Dict[str, Any]:
    """
    Guarantee required keys exist so downstream code doesn't KeyError.
    """
    if not isinstance(store, dict):
        store = {}
    store.setdefault("version", 1)
    store.setdefault("users", {})
    store.setdefault("awards", [])
    store.setdefault("stats", {})
    store["updated_at"] = _now_ts()
    return store


class XPAwardEventPersistOverlay(commands.Cog):
    """
    Listens to XP award events (xp_add, satpam_xp, xp.award) and
    persists a lightweight mirror into xp_store.json for dashboards / embeds.
    This overlay is deliberately defensive: it never assumes keys exist.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.path = _STORE_PATH
        log.info("[xp-persist] overlay active (file=%s)", self.path)

    async def _apply_award(self, user_id: int, amount: int, reason: Optional[str] = None) -> None:
        store = await _read_json(self.path)
        store = _ensure_store_shape(store)

        users = store["users"]
        u = users.get(str(user_id)) or users.get(user_id)  # support both string/int keys
        if not isinstance(u, dict):
            u = {
                "xp": 0,
                "level": "TK-L1",
                "awards": [],
                "updated_at": _now_ts(),
            }

        # mutate user entry
        u["xp"] = _safe_int(u.get("xp", 0), 0) + _safe_int(amount, 0)
        u["updated_at"] = _now_ts()  # previously keyed to store["updated_at"] -> caused KeyError
        if isinstance(u.get("awards"), list):
            u["awards"].append({
                "ts": _now_ts(),
                "amount": _safe_int(amount, 0),
                "reason": reason or "event",
            })
        else:
            u["awards"] = [{
                "ts": _now_ts(),
                "amount": _safe_int(amount, 0),
                "reason": reason or "event",
            }]

        # reattach
        users[str(user_id)] = u  # normalize to string key
        store["users"] = users
        store["updated_at"] = _now_ts()

        await _write_json(self.path, store)
        log.debug("[xp-persist] user=%s +%s OK (reason=%s)", user_id, amount, reason)

    # === Event listeners ===

    @commands.Cog.listener("on_xp_add")
    async def on_xp_add(self, **kwargs: Any) -> None:
        """
        Accepts flexible kwargs; normalize to (user_id, amount, reason).
        """
        try:
            uid = _safe_int(
                kwargs.get("user_id")
                or getattr(kwargs.get("author", None), "id", None)
                or kwargs.get("author_id")
                or kwargs.get("uid")
                , 0
            )
            amount = _safe_int(
                kwargs.get("amount")
                or kwargs.get("delta")
                or kwargs.get("xp")
                or 0, 0
            )
            reason = kwargs.get("reason") or "xp_add"
            if uid <= 0 or amount == 0:
                log.debug("[xp-persist] skip on_xp_add (uid=%s amount=%s)", uid, amount)
                return
            await self._apply_award(uid, amount, reason)
        except Exception:
            log.exception("[xp-persist] on_xp_add failed")

    @commands.Cog.listener("on_satpam_xp")
    async def on_satpam_xp(self, **kwargs: Any) -> None:
        try:
            uid = _safe_int(
                kwargs.get("user_id")
                or getattr(kwargs.get("author", None), "id", None)
                or kwargs.get("author_id")
                or kwargs.get("uid")
                , 0
            )
            amount = _safe_int(
                kwargs.get("amount")
                or kwargs.get("delta")
                or kwargs.get("xp")
                or 0, 0
            )
            reason = kwargs.get("reason") or "satpam_xp"
            if uid <= 0 or amount == 0:
                log.debug("[xp-persist] skip on_satpam_xp (uid=%s amount=%s)", uid, amount)
                return
            await self._apply_award(uid, amount, reason)
        except Exception:
            log.exception("[xp-persist] on_satpam_xp failed")

    @commands.Cog.listener("on_xp_award")
    async def on_xp_award(self, **kwargs: Any) -> None:
        try:
            uid = _safe_int(
                kwargs.get("user_id")
                or getattr(kwargs.get("author", None), "id", None)
                or kwargs.get("author_id")
                or kwargs.get("uid")
                , 0
            )
            amount = _safe_int(
                kwargs.get("amount")
                or kwargs.get("delta")
                or kwargs.get("xp")
                or 0, 0
            )
            reason = kwargs.get("reason") or "xp.award"
            if uid <= 0 or amount == 0:
                log.debug("[xp-persist] skip on_xp_award (uid=%s amount=%s)", uid, amount)
                return
            await self._apply_award(uid, amount, reason)
        except Exception:
            log.exception("[xp-persist] on_xp_award failed")


async def setup(bot: commands.Bot):
    await bot.add_cog(XPAwardEventPersistOverlay(bot))
