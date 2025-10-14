<<<<<<< HEAD
from __future__ import annotations
import datetime as dt
from satpambot.bot.modules.discord_bot.utils.kv_backend import get_kv_for

class WeeklyGate:
    def __init__(self):
        self.kv = get_kv_for("schedule")

    def should_run(self, name: str, now: dt.datetime | None = None) -> bool:
        now = now or dt.datetime.utcnow()
        y, w, _ = now.isocalendar()
        this_week = f"{y}-W{w:02d}"
        key = f"weekly:{name}"
        doc = self.kv.get_json(key) or {}
        last = doc.get("value")
        return last != this_week

    def mark_ran(self, name: str, now: dt.datetime | None = None) -> None:
        now = now or dt.datetime.utcnow()
        y, w, _ = now.isocalendar()
        this_week = f"{y}-W{w:02d}"
        key = f"weekly:{name}"
        self.kv.set_json(key, {"value": this_week})
=======

from __future__ import annotations
import datetime as dt
from satpambot.bot.modules.discord_bot.utils.atomic_json import AtomicJsonStore
class WeeklyGate:
    def __init__(self, path: str):
        self.store = AtomicJsonStore(path); self.store.load()
    def _key(self, name: str) -> str: return f'weekly::{name}'
    def should_run(self, name: str, now: dt.datetime | None = None) -> bool:
        now = now or dt.datetime.utcnow()
        last = self.store.get().get(self._key(name))
        y, w, _ = now.isocalendar(); this_week = f"{y}-W{w:02d}"
        return last != this_week
    def mark_ran(self, name: str, now: dt.datetime | None = None) -> None:
        now = now or dt.datetime.utcnow()
        y, w, _ = now.isocalendar(); val = f"{y}-W{w:02d}"
        self.store.update(lambda d: d.__setitem__(self._key(name), val))
>>>>>>> 377f4f2 (secure: remove local secrets; add safe example + improved pre-commit)
