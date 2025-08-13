# permissions helper (auto)
import os, json

CFG_FILE = os.getenv("MODULES_CONFIG_FILE","config/modules.json")

def _load_cfg():
    try:
        with open(CFG_FILE,'r',encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def exempt_roles():
    cfg = _load_cfg()
    return set((cfg.get("EXEMPT_ROLES") or []))

def whitelisted_channels():
    cfg = _load_cfg()
    return set((cfg.get("WHITELIST_CHANNELS") or []))

def is_exempt_user(member) -> bool:
    if not member: return False
    names = { (r.name if hasattr(r,'name') else str(r)).lower() for r in getattr(member,'roles',[]) }
    return any(er.lower() in names for er in exempt_roles())

def is_whitelisted_channel(channel) -> bool:
    if not channel: return False
    wl = {c.lstrip('#').lower() for c in whitelisted_channels()}
    return (getattr(channel,'name','').lower() in wl)
