# satpambot/shared/progress_gate.py
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict
import time


class Phase(str, Enum):
    TK = "TK"
    SD = "SD"
    # Future-ready (SMP, SMA, S1, S2, S3) if you want to extend later
    SMP = "SMP"
    SMA = "SMA"
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"


@dataclass
class ProgressState:
    tk: int = 0                # 0..100
    sd: int = 0                # 0..100
    public_allowed: bool = False
    last_prompt_at: float = 0.0

    shadow_seen: int = 0
    shadow_correct: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def both_100(self) -> bool:
        return self.tk >= 100 and self.sd >= 100

    @property
    def shadow_accuracy(self) -> float:
        if self.shadow_seen <= 0:
            return 0.0
        return round(self.shadow_correct / max(1, self.shadow_seen) * 100.0, 2)


class ProgressGate:
    """
    File-backed progress gate with a simple JSON store (no ENV required).
    Thread-safe; safe to call from discord tasks/threads.
    """
    def __init__(self, store_path: Path):
        self._store_path = Path(store_path)
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._state = ProgressState()
        self._load()

    # ---------- Persistence ----------
    def _load(self) -> None:
        with self._lock:
            if self._store_path.exists():
                try:
                    data = json.loads(self._store_path.read_text(encoding="utf-8"))
                except Exception:
                    data = {}
                self._state = ProgressState(**{
                    "tk": int(data.get("tk", 0)),
                    "sd": int(data.get("sd", 0)),
                    "public_allowed": bool(data.get("public_allowed", False)),
                    "last_prompt_at": float(data.get("last_prompt_at", 0.0)),
                    "shadow_seen": int(data.get("shadow_seen", 0)),
                    "shadow_correct": int(data.get("shadow_correct", 0)),
                })
            else:
                self._save_unlocked()

    def _save_unlocked(self) -> None:
        self._store_path.write_text(json.dumps(self._state.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def save(self) -> None:
        with self._lock:
            self._save_unlocked()

    # ---------- Getters ----------
    def state(self) -> ProgressState:
        with self._lock:
            return ProgressState(**self._state.as_dict())  # return a copy

    # ---------- Mutations ----------
    def set_phase_value(self, tk: int = None, sd: int = None) -> ProgressState:
        with self._lock:
            if tk is not None:
                self._state.tk = max(0, min(100, int(tk)))
            if sd is not None:
                self._state.sd = max(0, min(100, int(sd)))
            self._save_unlocked()
            return self.state()

    def bump_shadow_eval(self, correct: bool) -> ProgressState:
        with self._lock:
            self._state.shadow_seen += 1
            if correct:
                self._state.shadow_correct += 1
            self._save_unlocked()
            return self.state()

    def allow_public(self) -> ProgressState:
        with self._lock:
            self._state.public_allowed = True
            self._save_unlocked()
            return self.state()

    def lock_public(self) -> ProgressState:
        with self._lock:
            self._state.public_allowed = False
            self._save_unlocked()
            return self.state()

    def mark_prompted_now(self) -> None:
        with self._lock:
            self._state.last_prompt_at = time.time()
            self._save_unlocked()

    # ---------- Policies ----------
    def is_public_allowed(self) -> bool:
        with self._lock:
            return bool(self._state.public_allowed)

    def should_prompt_owner(self, min_interval_sec: int = 12 * 3600) -> bool:
        with self._lock:
            if not self._state.both_100:
                return False
            now = time.time()
            if now - float(self._state.last_prompt_at or 0.0) >= float(min_interval_sec):
                return True
            return False

    # ---------- Derived Data ----------
    def summary_lines(self):
        s = self.state()
        phase_line = f"Phase: TK={s.tk}%, SD={s.sd}% — {'COMPLETE ✅' if s.both_100 else 'In progress…'}"
        gate_line = f"Public Chat: {'ENABLED ✅' if s.public_allowed else 'SILENT (Shadow-Mode) 🔒'}"
        acc_line = f"Shadow Accuracy: {s.shadow_accuracy:.2f}% ({s.shadow_correct}/{s.shadow_seen})"
        return phase_line, gate_line, acc_line
