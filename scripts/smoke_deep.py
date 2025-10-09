
"""
Deep smoke test for SatpamLeina repo.

Goals:
- Import every cog module safely (offline).
- If a module exposes async setup(bot), call it TWICE and ensure idempotency:
  * no extra cog registrations
  * no extra listeners
  * no extra background tasks scheduled
- Capture logs emitted during setup to catch duplicate noisy lines.
- Report any top-level (module import time) task creation.
- Summarize required ENV keys referenced via os.getenv and whether they are set.

Usage:
    python scripts/smoke_deep.py [--package satpambot.bot.modules.discord_bot.cogs] [--strict]

Notes:
- Does NOT require DISCORD_TOKEN / BOT_TOKEN.
- No network calls.
"""

import argparse
import asyncio
import importlib
import inspect
import logging
import os
import pkgutil
import re
import sys
import time
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# ---------------- Logger capture ----------------

class LogCaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records: List[Tuple[float, str, str]] = []  # (ts, level, message)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        self.records.append((time.time(), record.levelname, msg))

    def snapshot(self) -> int:
        return len(self.records)

    def dupes_since(self, idx: int) -> List[Tuple[str, int]]:
        counts: Dict[str, int] = {}
        for _, _, m in self.records[idx:]:
            counts[m] = counts.get(m, 0) + 1
        return [(m, n) for (m, n) in counts.items() if n > 1]


# ---------------- Dummy asyncio Task & Loop ----------------

class DummyTask:
    _id_seq = 0
    def __init__(self, coro):
        type(self)._id_seq += 1
        self.id = type(self)._id_seq
        self.coro = coro
        self._done = False
        self._name = getattr(coro, "__name__", f"task-{self.id}")
    def cancel(self): pass
    def done(self): return self._done
    def __repr__(self) -> str:
        return f"<DummyTask id={self.id} name={self._name}>"

class DummyLoop:
    def __init__(self):
        self.tasks: List[DummyTask] = []
    def create_task(self, coro):
        t = DummyTask(coro)
        self.tasks.append(t)
        return t


# ---------------- Dummy Bot ----------------

class DummyBot:
    def __init__(self, logger: logging.Logger):
        self.loop = DummyLoop()
        self._cogs: Dict[str, Any] = {}
        self._listeners: List[Tuple[Callable, Optional[str]]] = []
        self._checks: List[Callable] = []
        self._logger = logger
        self.user = SimpleNamespace(id=0, name="DummyUser#0000")

    # "discord.py v2 style" add_cog is async; support both
    async def add_cog(self, cog, **kwargs):
        name = type(cog).__name__
        self._cogs[name] = cog
        return cog

    def remove_cog(self, name: str):
        self._cogs.pop(name, None)

    def add_listener(self, callback, name: Optional[str]=None):
        self._listeners.append((callback, name))

    def remove_listener(self, callback, name: Optional[str]=None):
        try:
            self._listeners.remove((callback, name))
        except ValueError:
            pass

    def add_check(self, fn):
        self._checks.append(fn)

    def remove_check(self, fn):
        try:
            self._checks.remove(fn)
        except ValueError:
            pass

    # commonly accessed helpers in cogs
    async def wait_until_ready(self): return
    def is_closed(self): return False
    def get_guild(self, gid): return None
    def get_channel(self, cid): return None
    async def fetch_channel(self, cid): return None


# ---------------- Utilities ----------------

ENV_PATTERN = re.compile(r"os\.getenv\(\s*['\"]([A-Z0-9_]+)['\"]")

def find_env_keys(module) -> Set[str]:
    keys: Set[str] = set()
    try:
        src = inspect.getsource(module)
    except Exception:
        return keys
    for m in ENV_PATTERN.finditer(src):
        keys.add(m.group(1))
    return keys

def is_cog_module(mod) -> bool:
    # treat any module under the cogs package as a cog module
    return True

def iter_modules(pkgname: str):
    pkg = importlib.import_module(pkgname)
    prefix = pkg.__name__ + "."
    for m in pkgutil.walk_packages(pkg.__path__, prefix):
        yield m.name

def format_delta(a: dict, b: dict) -> dict:
    delta = {}
    for k in a.keys():
        if a[k] != b[k]:
            delta[k] = {"before": a[k], "after": b[k]}
    return delta


# ---------------- Deep smoke ----------------

async def deep_check(pkgname: str, strict: bool=False) -> int:
    logger = logging.getLogger("deep-smoke")
    logger.setLevel(logging.INFO)
    cap = LogCaptureHandler()
    cap.setFormatter(logging.Formatter("%(name)s:%(message)s"))
    logging.getLogger().addHandler(cap)

    exit_code = 0
    report: List[str] = []
    env_keys_used: Set[str] = set()

    for modname in sorted(iter_modules(pkgname)):
        if modname.endswith(".__main__"):
            continue
        try:
            mod = importlib.import_module(modname)
        except Exception as e:
            exit_code = 1
            report.append(f"FAIL import: {modname} :: {e.__class__.__name__}: {e}")
            continue

        if not is_cog_module(mod):
            continue

        env_keys_used |= find_env_keys(mod)

        bot = DummyBot(logger)

        state_before = {
            "cogs": len(bot._cogs),
            "listeners": len(bot._listeners),
            "tasks": len(bot.loop.tasks),
        }

        setup_fn = getattr(mod, "setup", None)
        # Import-time tasks (bad smell)
        import_time_tasks = len(bot.loop.tasks)

        if setup_fn and inspect.iscoroutinefunction(setup_fn):
            idx0 = cap.snapshot()
            try:
                await setup_fn(bot)
            except Exception as e:
                exit_code = 1
                report.append(f"FAIL setup: {modname} :: {e.__class__.__name__}: {e}")
                continue
            idx1 = cap.snapshot()

            state_after_once = {
                "cogs": len(bot._cogs),
                "listeners": len(bot._listeners),
                "tasks": len(bot.loop.tasks),
            }

            # Call setup again to test idempotency
            try:
                await setup_fn(bot)
            except Exception as e:
                exit_code = 1
                report.append(f"FAIL setup(2nd): {modname} :: {e.__class__.__name__}: {e}")
                continue

            state_after_twice = {
                "cogs": len(bot._cogs),
                "listeners": len(bot._listeners),
                "tasks": len(bot.loop.tasks),
            }

            # Check deltas
            delta_first = format_delta(state_before, state_after_once)
            delta_second = format_delta(state_after_once, state_after_twice)

            issues = []

            if import_time_tasks:
                issues.append(f"import scheduled {import_time_tasks} tasks at import time")

            # Non-idempotent if second call changed anything
            if delta_second:
                issues.append(f"non-idempotent setup (2nd call changed state: {delta_second})")

            # Check duplicate logs during first setup burst
            dupes = cap.dupes_since(idx0)
            noisy = [f"'{m}' x{n}" for (m, n) in dupes if n > 1]
            if noisy:
                issues.append("noisy logs: " + "; ".join(noisy))

            if issues:
                status = "WARN" if not strict else "FAIL"
                if strict: exit_code = 1
                report.append(f"{status}: {modname} -> " + " ; ".join(issues))
            else:
                report.append(f"OK   : {modname} — idempotent, quiet")
        else:
            report.append(f"OK   : {modname} — no setup() — import ok")

    # Summarize ENV keys used
    env_summary = []
    for k in sorted(env_keys_used):
        v = os.getenv(k)
        env_summary.append((k, "SET" if (v is not None and v != "") else "unset"))

    print("== Deep Smoke Report ==")
    for line in report:
        print(line)

    print("\n== ENV Keys referenced (scan) ==")
    for k, s in env_summary:
        print(f"{k} : {s}")

    logging.getLogger().removeHandler(cap)
    return exit_code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", default="satpambot.bot.modules.discord_bot.cogs")
    ap.add_argument("--strict", action="store_true", help="treat WARN as FAIL")
    args = ap.parse_args()

    # Force logging baseline
    logging.basicConfig(level=logging.INFO)

    try:
        exit_code = asyncio.run(deep_check(args.package, strict=args.strict))
    except RuntimeError as e:
        # In case of nested event loop (on some IDEs), fallback
        loop = asyncio.get_event_loop()
        exit_code = loop.run_until_complete(deep_check(args.package, strict=args.strict))

    if exit_code == 0:
        print("\nOK: deep smoke passed.")
    else:
        print("\nDONE: deep smoke finished with issues.")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
