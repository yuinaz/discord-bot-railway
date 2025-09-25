# cf_login_guard.py — Persisted backoff for Discord login 429 / Cloudflare 1015
from __future__ import annotations
import json, time, random, pathlib, logging

log = logging.getLogger(__name__)

_STATE_DIRS = ["/data/satpambot_state", "/tmp"]
_STATE_FILE = "cf_login_guard.json"

def _state_path():
    for d in _STATE_DIRS:
        try:
            p = pathlib.Path(d); p.mkdir(parents=True, exist_ok=True); return p / _STATE_FILE
        except Exception: continue
    return pathlib.Path("/tmp") / _STATE_FILE

def _now() -> float: return time.time()

def load_state():
    p = _state_path()
    try:
        return json.loads(p.read_text("utf-8"))
    except Exception:
        return {}

def save_state(s):
    try:
        _state_path().write_text(json.dumps(s, ensure_ascii=False, indent=2))
    except Exception:
        pass

def suggested_sleep() -> float:
    s = load_state()
    until = float(s.get("banned_until_ts", 0.0))
    remain = until - _now()
    return max(0.0, remain)

def mark_429(ray_id: str | None = None, retry_after_hint: float | None = None):
    """Mark ban window with conservative duration. CF 1015 often needs minutes."""
    base = float(retry_after_hint or 0.0)
    if base <= 0: base = 60.0
    # be conservative: 5x hinted or at least 5 minutes
    window = max(300.0, min(1800.0, base * 5.0))
    # add jitter (0..60s) to avoid thundering-herd
    window += random.uniform(10.0, 60.0)
    s = load_state()
    s["banned_until_ts"] = _now() + window
    if ray_id: s["last_ray_id"] = ray_id
    save_state(s)
    log.warning("[cf_login_guard] 429/1015 noted; backoff %.1fs (RayID=%s)", window, ray_id or "-")
