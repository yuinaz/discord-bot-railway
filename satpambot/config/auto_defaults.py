
from __future__ import annotations
import os, json
from pathlib import Path

_DEFAULTS = {
    "XP_SENIOR_KEY": "xp:bot:senior_total_v2",
    "LEARNING_MIN_LABEL": "KULIAH-S2",
    "LEINA_PRESENCE_TEMPLATE": "🎓 {label} • {percent:.1f}%",
    "QNA_CHANNEL_ID": 1426571542627614772,
    "AUTOLEARN_DEDUP_ENABLED": True,
    "AUTOLEARN_DEDUP_DELETE_DELAY_MS": 900,
    "QNA_XP_PER_ANSWER_BOT": 5,
    "QNA_AWARD_IDEMP_NS": "qna:awarded:answer",
    "LOG_BOTPHISHING_CHANNEL_ID": 1400375184048787566,
    "LOG_BOTPHISHING_STICKY_TITLE": "Leina — Bot Phishing Log",
    "LOG_BOTPHISHING_STICKY_TEXT": "📌 Referensi pHash & catatan operasi. Pesan ini akan diupdate otomatis.",
    "BOT_TZ": "Asia/Jakarta",
    "NEURO_LITE_PROGRESS_CHANNEL_ID": 0,
    "NEURO_LITE_PROGRESS_TIME_HOUR": 21,
    "NEURO_LITE_PROGRESS_TIME_MINUTE": 0,
    "WEEKLY_XP_IDEMPOTENT_NS": "weekly_xp:done_week",
    "WEEKLY_XP_TITLE_PREFIX": "Weekly Random XP",
}

def _load_json_overrides() -> dict:
    here = Path(__file__).resolve()
    root = here.parents[1]  # .../satpambot
    p = root / "data" / "config" / "auto_defaults.json"
    if p.exists():
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    return {}

_JSON = _load_json_overrides()

def cfg_str(key: str, default: str | None = None) -> str | None:
    v = os.getenv(key)
    if v is not None:
        return v
    v = _JSON.get(key)
    if v is not None:
        return str(v)
    return _DEFAULTS.get(key, default) if key in _DEFAULTS else default

def cfg_int(key: str, default: int | None = None) -> int | None:
    v = os.getenv(key)
    if v is not None:
        try: return int(v)
        except Exception: pass
    v = _JSON.get(key)
    if v is not None:
        try: return int(v)
        except Exception: pass
    return int(_DEFAULTS.get(key, default)) if key in _DEFAULTS else default

def cfg_bool(key: str, default: bool | None = None) -> bool | None:
    v = os.getenv(key)
    if v is not None:
        return v.lower() in ("1","true","yes","on")
    v = _JSON.get(key)
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() in ("1","true","yes","on")
    if key in _DEFAULTS:
        return bool(_DEFAULTS[key])
    return default
