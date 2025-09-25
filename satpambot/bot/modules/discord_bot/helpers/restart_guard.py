
import os, time, json, pathlib, logging
log = logging.getLogger(__name__)

GUARD_FILE = os.getenv("SB_RESTART_GUARD_FILE", "/tmp/satpambot_restart.lock")
WINDOW_SEC = int(os.getenv("SB_RESTART_WINDOW_SEC", "240"))  # 4 minutes

def guard_status():
    p = pathlib.Path(GUARD_FILE)
    try:
        return p.exists(), (time.time() - p.stat().st_mtime) if p.exists() else None
    except Exception:
        return False, None

def mark(reason="unknown"):
    p = pathlib.Path(GUARD_FILE)
    try:
        p.write_text(json.dumps({"t": time.time(), "reason": reason}, ensure_ascii=False))
        return True
    except Exception as e:
        log.warning("[restart_guard] failed write: %r", e)
        return False

def clear():
    try:
        pathlib.Path(GUARD_FILE).unlink(missing_ok=True)
        return True
    except Exception as e:
        log.warning("[restart_guard] failed clear: %r", e)
        return False

def should_restart():
    exists, age = guard_status()
    return not (exists and age is not None and age < WINDOW_SEC), age
