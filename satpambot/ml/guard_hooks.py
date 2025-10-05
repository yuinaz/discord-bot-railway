# -*- coding: utf-8 -*-
"""Minimal guard hooks shim for injected cogs.
Provides GuardAdvisor (backoff + error squelch) and @guard_hook decorator.
Safe for Render free plan: no extra deps, no config changes.
"""
from __future__ import annotations

import asyncio
import functools
import logging
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])

@dataclass
class BackoffState:
    consecutive_errors: int = 0
    last_error_ts: float = 0.0
    backoff_until: float = 0.0

    def next_sleep(self, base: float = 1.0, cap: float = 30.0) -> float:
        # Exponential backoff (1s, 2s, 4s, 8s, ... up to cap)
        step = max(0, self.consecutive_errors - 1)
        return min(cap, base * (2 ** step))

class GuardAdvisor:
    """Tracks failures per-key and recommends short backoffs to avoid spam/crash loops."""

    def __init__(
        self,
        name: str = "guard",
        error_window_seconds: int = 60,
        max_errors_per_window: int = 30,
    ) -> None:
        self.name = name
        self.error_window_seconds = error_window_seconds
        self.max_errors_per_window = max_errors_per_window
        self.log = logging.getLogger(f"{__name__}.{name}")
        self._states: Dict[str, BackoffState] = {}

    def should_suppress(self, key: str) -> bool:
        st = self._states.get(key)
        if not st:
            return False
        return time.time() < st.backoff_until

    def record_success(self, key: str) -> None:
        st = self._states.setdefault(key, BackoffState())
        st.consecutive_errors = 0
        st.backoff_until = 0.0

    def record_error(self, key: str, exc: BaseException) -> float:
        st = self._states.setdefault(key, BackoffState())
        st.consecutive_errors += 1
        st.last_error_ts = time.time()
        sleep = st.next_sleep()
        st.backoff_until = st.last_error_ts + sleep
        self._log_error(key, exc, sleep)
        return sleep

    def _log_error(self, key: str, exc: BaseException, sleep: float) -> None:
        try:
            self.log.warning("[guard] %s failed (%s); backoff=%.1fs", key, exc.__class__.__name__, sleep)
            # Detailed stack kept at DEBUG to keep Render logs clean
            self.log.debug("Exception details", exc_info=exc)
        except Exception:
            pass

_global_advisor: Optional[GuardAdvisor] = None

def _get_advisor() -> GuardAdvisor:
    global _global_advisor
    if _global_advisor is None:
        _global_advisor = GuardAdvisor("global")
    return _global_advisor

def guard_hook(fn: F) -> F:
    """Decorator to guard async handlers (e.g., on_message) from crash loops.
    - Swallows exceptions and applies short exponential backoff per function key.
    - Returns None on suppress/error; preserves original return otherwise.
    """
    if not asyncio.iscoroutinefunction(fn):
        # Support sync functions by wrapping into async
        @functools.wraps(fn)
        async def _sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            advisor = _get_advisor()
            key = f"{fn.__module__}.{fn.__name__}"
            if advisor.should_suppress(key):
                return None
            try:
                result = fn(*args, **kwargs)
                advisor.record_success(key)
                return result
            except BaseException as e:  # noqa: BLE001
                advisor.record_error(key, e)
                return None
        return _sync_wrapper  # type: ignore[misc]

    @functools.wraps(fn)
    async def _wrapper(*args: Any, **kwargs: Any) -> Any:
        advisor = _get_advisor()
        key = f"{fn.__module__}.{fn.__name__}"
        if advisor.should_suppress(key):
            return None
        try:
            result = await fn(*args, **kwargs)
            advisor.record_success(key)
            return result
        except BaseException as e:  # noqa: BLE001
            advisor.record_error(key, e)
            return None

    return _wrapper  # type: ignore[misc]

__all__ = ["guard_hook", "GuardAdvisor", "BackoffState"]
