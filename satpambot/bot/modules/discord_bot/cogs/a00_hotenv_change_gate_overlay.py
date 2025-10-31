
# a00_hotenv_change_gate_overlay.py
# Goal: Only allow `hotenv_reload` AFTER startup AND when config files REALLY changed.
# - Blocks false positives at startup.
# - Verifies change by hashing watched files.
# - Composes with other dispatch patches (wraps current Bot.dispatch).

import os
import io
import glob
import time
import asyncio
import logging
import hashlib
from typing import Dict, Tuple
from discord.ext import commands

_PATCH_FLAG = "_patched_by_hotenv_change_gate"

# Config via ENV
# Comma-separated globs; default covers common json/yaml in data/config plus overrides & runtime_env.
_DEFAULT_GLOBS = [
    "data/config/**/*.json",
    "data/config/**/*.yml",
    "data/config/**/*.yaml",
    "**/overrides*.json",
    "**/runtime_env.json",
]
_WATCH_GLOBS = [g for g in os.getenv("HOTENV_WATCH_GLOB", "").split(",") if g.strip()] or _DEFAULT_GLOBS

# Startup grace: suppress hotenv until on_ready or grace time elapsed
_STARTUP_GRACE_MS = int(os.getenv("HOTENV_STARTUP_GRACE_MS", "2500"))

# State
_boot_ready = False
_boot_t0 = time.monotonic()
_baseline: Dict[str, Tuple[float, int, str]] = {}  # path -> (mtime, size, sha256)

def _iter_files():
    seen = set()
    for pat in _WATCH_GLOBS:
        for path in glob.glob(pat, recursive=True):
            if not os.path.isfile(path):
                continue
            # Normalize & dedupe
            try:
                norm = os.path.normpath(path)
            except Exception:
                norm = path
            if norm in seen:
                continue
            seen.add(norm)
            yield norm

def _hash_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def _snapshot() -> Dict[str, Tuple[float, int, str]]:
    snap = {}
    for p in _iter_files():
        try:
            st = os.stat(p)
            mtime = st.st_mtime
            size = st.st_size
            sh = _hash_file(p)
            snap[p] = (mtime, size, sh)
        except FileNotFoundError:
            # File disappeared; skip
            continue
        except Exception as e:
            logging.exception("[hotenv-change] snapshot error for %s: %r", p, e)
    return snap

def _has_changed() -> bool:
    global _baseline
    # Fast path: compare mtime+size first; hash only if candidate differs
    current_meta = {}
    changed = False
    for p in _iter_files():
        try:
            st = os.stat(p)
            meta = (st.st_mtime, st.st_size)
            current_meta[p] = meta
            base = _baseline.get(p)
            if not base or (base[0] != meta[0] or base[1] != meta[1]):
                # Potential change -> compute hash
                try:
                    sh = _hash_file(p)
                except FileNotFoundError:
                    sh = ""
                if not base or base[2] != sh:
                    logging.debug("[hotenv-change] file changed: %s", p)
                    changed = True
        except FileNotFoundError:
            if p in _baseline:
                logging.debug("[hotenv-change] file removed: %s", p)
                changed = True
        except Exception as e:
            logging.exception("[hotenv-change] stat error for %s: %r", p, e)

    # Also detect newly-added files
    for p in _baseline.keys():
        if p not in current_meta:
            logging.debug("[hotenv-change] baseline file missing now: %s", p)
            changed = True

    return changed

def _refresh_baseline():
    global _baseline
    _baseline = _snapshot()
    logging.warning("[hotenv-change] baseline refreshed: %d file(s)", len(_baseline))

def _patch_dispatch():
    Bot = commands.Bot
    if getattr(Bot.dispatch, _PATCH_FLAG, False):
        return

    original_dispatch = Bot.dispatch  # may already be patched by other overlays

    def patched_dispatch(self, event_name, *args, **kwargs):
        if event_name != "hotenv_reload":
            return original_dispatch(self, event_name, *args, **kwargs)

        # Cold-start guard
        elapsed_ms = int((time.monotonic() - _boot_t0) * 1000)
        if not _boot_ready and elapsed_ms < _STARTUP_GRACE_MS:
            logging.warning("[hotenv-change] drop hotenv_reload during startup (elapsed=%dms < %dms)", elapsed_ms, _STARTUP_GRACE_MS)
            return  # swallow event

        # Change detection
        try:
            if not _has_changed():
                logging.warning("[hotenv-change] ignored hotenv_reload (no config change)")
                return  # swallow event
        except Exception as e:
            logging.exception("[hotenv-change] change check failed: %r (allowing reload)")

        # Update baseline and forward event
        _refresh_baseline()
        return original_dispatch(self, event_name, *args, **kwargs)

    patched_dispatch.__dict__[_PATCH_FLAG] = True
    Bot.dispatch = patched_dispatch
    logging.warning("[hotenv-change] Bot.dispatch patched (startup+change gate; watch=%s)", ", ".join(_WATCH_GLOBS))

class _HotenvReadyFlag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        global _boot_ready
        if not _baseline:
            _refresh_baseline()
        _boot_ready = True
        logging.warning("[hotenv-change] on_ready: hotenv gating is now active (startup complete)")

async def setup(bot):
    _patch_dispatch()
    await bot.add_cog(_HotenvReadyFlag(bot))
    logging.debug("[hotenv-change] overlay setup complete")
