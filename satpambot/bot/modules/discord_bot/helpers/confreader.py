from __future__ import annotations
import os, json, threading
from pathlib import Path
from typing import Any, Optional

# Simple cached JSON config loader. Preference order:
# 1) data/config/runtime_env.json
# 2) data/config/overrides.render-free.json
# 3) data/config/passive_bridge.json
# Fallback to os.environ

_CFG_CACHE: dict[str, Any] = {}
_CFG_LOCK = threading.Lock()
_CFG_FILES = [
    Path("data/config/runtime_env.json"),
    Path("data/config/overrides.render-free.json"),
    Path("data/config/passive_bridge.json"),
]

def _load_cfg() -> dict[str, Any]:
    with _CFG_LOCK:
        if _CFG_CACHE:
            return _CFG_CACHE
        cfg: dict[str, Any] = {}
        for p in _CFG_FILES:
            try:
                if p.exists():
                    d = json.loads(p.read_text(encoding="utf-8"))
                    # allow "env": {...} or top-level
                    if isinstance(d, dict):
                        if "env" in d and isinstance(d["env"], dict):
                            cfg.update(d["env"])
                        cfg.update({k: v for k, v in d.items() if k != "env"})
            except Exception:
                # ignore malformed file
                pass
        _CFG_CACHE.update(cfg)
        return _CFG_CACHE

def cfg_str(key: str, default: Optional[str] = None) -> Optional[str]:
    try:
        # If project already has cfg_str, respect it
        from satpambot.config.auto_defaults import cfg_str as real_cfg_str  # type: ignore
        val = real_cfg_str(key, default)
        if val is not None:
            return val
    except Exception:
        pass
    cfg = _load_cfg()
    if key in cfg and isinstance(cfg[key], str):
        return cfg[key]
    # final fallback to env
    return os.getenv(key, default) if default is not None else os.getenv(key)

def cfg_int(key: str, default: int) -> int:
    v = cfg_str(key, None)
    try:
        return int(v) if v is not None else int(default)
    except Exception:
        return int(default)

def cfg_float(key: str, default: float) -> float:
    v = cfg_str(key, None)
    try:
        return float(v) if v is not None else float(default)
    except Exception:
        return float(default)