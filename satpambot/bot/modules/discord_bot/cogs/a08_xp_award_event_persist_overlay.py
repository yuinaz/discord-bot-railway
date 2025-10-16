
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

from discord.ext import commands


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)  # type: ignore[arg-type]
    except Exception:
        return default


class XPAwardEventPersistOverlay(commands.Cog):
    """
    Listener yang menyimpan XP ke file `satpambot/bot/data/xp_store.json`.
    - Tahan banting terhadap berbagai bentuk event args (positional/kwargs).
    - Tidak lagi error saat kunci 'updated_at' tidak ada.
    """

    STORE_PATH = "satpambot/bot/data/xp_store.json"

    def __init__(self, bot):
        self.bot = bot

    # ---- helpers ---------------------------------------------------------

    def _load_store(self) -> dict:
        try:
            with open(self.STORE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

        # normalize structure
        data.setdefault("version", 2)
        data.setdefault("users", {})
        data.setdefault("awards", {})
        data.setdefault("stats", {})
        data["updated_at"] = _now_iso()
        return data

    def _save_store(self, data: dict) -> None:
        os.makedirs(os.path.dirname(self.STORE_PATH), exist_ok=True)
        with open(self.STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def _apply_award(self, user_id: int, amount: int, reason: Optional[str]) -> None:
        store = self._load_store()
        users = store["users"]

        key = str(user_id)
        user = users.get(key, {"xp": 0, "awards": []})
        user["xp"] = _safe_int(user.get("xp", 0)) + _safe_int(amount, 0)
        user["updated_at"] = store["updated_at"]

        if reason:
            awards = user.get("awards", [])
            awards.append({"amount": _safe_int(amount, 0), "reason": reason, "ts": store["updated_at"]})
            # keep last 50 to avoid bloating the file
            user["awards"] = awards[-50:]

        users[key] = user
        self._save_store(store)

    # ---- listeners -------------------------------------------------------

    @commands.Cog.listener()
    async def on_xp_add(self, *args, **kwargs):
        """
        Menerima berbagai bentuk event:
        - on_xp_add(user_id, amount, reason)
        - on_xp_add(user_id=..., amount=..., reason=...)
        - alias uid untuk user_id juga diterima
        """
        user_id = None
        amount = None
        reason = None

        # positional style
        if args and isinstance(args[0], int):
            user_id = args[0]
            amount = args[1] if len(args) > 1 else 1
            reason = args[2] if len(args) > 2 else None
        else:
            # kwargs style
            user_id = kwargs.get("user_id") or kwargs.get("uid")
            amount = kwargs.get("amount", 1)
            reason = kwargs.get("reason")

        if user_id is None:
            return

        await self._apply_award(int(user_id), _safe_int(amount, 1), reason)

    @commands.Cog.listener()
    async def on_satpam_xp(self, *args, **kwargs):
        # gunakan handler yang sama
        await self.on_xp_add(*args, **kwargs)


async def setup(bot):
    await bot.add_cog(XPAwardEventPersistOverlay(bot))
