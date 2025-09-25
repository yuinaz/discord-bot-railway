# satpambot/bot/modules/discord_bot/helpers/cf_login_guard.py
from __future__ import annotations
import json, time, random, pathlib, logging
log = logging.getLogger(__name__)
_STATE_DIRS = ["/data/satpambot_state", "/tmp"]
_STATE_FILE = "cf_login_guard.json"

def _path():
    for d in _STATE_DIRS:
        try:
            p = pathlib.Path(d); p.mkdir(parents=True, exist_ok=True); return p / _STATE_FILE
        except Exception: continue
    return pathlib.Path("/tmp") / _STATE_FILE

def _now(): return time.time()

def load_state():
    try: return json.loads(_path().read_text("utf-8"))
    except Exception: return {}

def save_state(s):
    try: _path().write_text(json.dumps(s, ensure_ascii=False, indent=2))
    except Exception: pass

def suggested_sleep() -> float:
    s = load_state(); return max(0.0, float(s.get("banned_until_ts", 0.0)) - _now())

def mark_429(ray_id: str | None = None, retry_after_hint: float | None = None):
    base = float(retry_after_hint or 0.0)
    # Wider default window to avoid re-tripping CF 1015
    if base <= 0: base = 600.0  # 10 min
    window = max(600.0, min(1500.0, base * 1.5)) + random.uniform(15.0, 75.0)
    s = load_state(); s["banned_until_ts"] = _now() + window
    if ray_id: s["last_ray_id"] = ray_id
    save_state(s)
    log.warning("[cf_login_guard] backoff %.1fs (RayID=%s)", window, ray_id or "-")
