
from __future__ import annotations
import os, json
from pathlib import Path
from typing import Any, Dict

CFG_PATH = Path(__file__).resolve().parents[2] / 'satpambot_config.local.json'
SECRETS_DIR = Path(__file__).resolve().parents[2] / 'secrets'

DEFAULTS: Dict[str, Any] = {
    'OWNER_USER_ID': None,
    'COMMANDS_OWNER_ONLY': True,
    'UPDATE_DM_OWNER': True,
    'MAINTENANCE_AUTO': True,
    'MAINT_HALF_CPU': 85,
    'MAINT_RESUME_CPU': 50,
    'NAP_ENABLE': True,
    'NAP_DM_NOTIF': False,
    'NAP_MAX_OFF': 30,
    'NAP_MIN_OFF': 2,
    'NAP_MIN_ON': 10,
    'NAP_MAX_ON': 60,
    'NAP_CPU_LOW': 20.0,
    'NAP_CPU_HIGH': 75.0,
    'NAP_MSG_LOW': 2.0,
    'NAP_MSG_HIGH': 25.0,
    'NAP_ADAPT_ALPHA': 0.3,
    'STICKER_ENABLE': False,
    'DISABLED_COGS': 'name_wake_autoreply',
    'BOOT_DM_ONLINE': False,
    'OPENAI_TIMEOUT_S': 20,
    'SELF_LEARNING_ENABLE': True,
    'SELF_LEARNING_SAFETY': 'conservative',
    'PORT': 10000,
}

def _read_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        pass
    return {}

def _write_json(path: Path, data: Dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(path)
    except Exception:
        pass

_LOCAL = _read_json(CFG_PATH)

def _parse_bool(v: Any) -> bool:
    if isinstance(v, bool): return v
    s = str(v).strip().lower()
    return s in ('1','true','yes','on','y')

def _coerce(k: str, v: Any) -> Any:
    if k in ('COMMANDS_OWNER_ONLY','UPDATE_DM_OWNER','MAINTENANCE_AUTO','NAP_ENABLE','NAP_DM_NOTIF','STICKER_ENABLE','BOOT_DM_ONLINE','SELF_LEARNING_ENABLE'):
        return _parse_bool(v)
    if k in ('MAINT_HALF_CPU','MAINT_RESUME_CPU','PORT'):
        try: return int(v)
        except: return DEFAULTS.get(k, v)
    if k in ('NAP_MAX_OFF','NAP_MIN_OFF','NAP_MIN_ON','NAP_MAX_ON','OPENAI_TIMEOUT_S'):
        try: return int(v)
        except: return DEFAULTS.get(k, v)
    if k in ('NAP_CPU_LOW','NAP_CPU_HIGH','NAP_MSG_LOW','NAP_MSG_HIGH','NAP_ADAPT_ALPHA'):
        try: return float(v)
        except: return DEFAULTS.get(k, v)
    if k == 'OWNER_USER_ID':
        return None if v in (None,'', 'None', 'null') else str(v)
    return v

def cfg(key: str, default: Any = None) -> Any:
    if key in _LOCAL:
        return _coerce(key, _LOCAL[key])
    if key in os.environ:
        return _coerce(key, os.environ[key])
    if key in DEFAULTS:
        return DEFAULTS[key] if default is None else _coerce(key, DEFAULTS.get(key, default))
    return default

def set_cfg(key: str, value: Any) -> None:
    _LOCAL[key] = value
    _write_json(CFG_PATH, _LOCAL)

def set_secret(name: str, value: str) -> None:
    data = _read_json(CFG_PATH)
    sec = data.get('secrets') or {}
    sec[name] = value
    data['secrets'] = sec
    _write_json(CFG_PATH, data)

def all_cfg() -> Dict[str, Any]:
    out = dict(DEFAULTS)
    out.update({k: _coerce(k, v) for k, v in _LOCAL.items()})
    return out

def get_secret(name: str) -> str | None:
    if name in os.environ and os.environ.get(name):
        return os.environ.get(name)
    try:
        data = _read_json(CFG_PATH)
        sec = data.get('secrets') or {}
        if name in sec and sec[name]:
            return str(sec[name])
    except Exception:
        pass
    try:
        SECRETS_DIR.mkdir(parents=True, exist_ok=True)
        candidate = SECRETS_DIR / f"{name.lower()}.txt"
        if candidate.exists():
            return candidate.read_text(encoding='utf-8').strip()
    except Exception:
        pass
    return None
