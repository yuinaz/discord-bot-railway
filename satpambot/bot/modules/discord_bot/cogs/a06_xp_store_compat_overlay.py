
import os, json, time, datetime
from pathlib import Path
from typing import Any, Dict

from discord.ext import commands

# ---- Tiny Upstash REST helper (no external deps) ----
try:
    from urllib.parse import quote as _quote
    from urllib.request import Request, urlopen
except Exception:  # pragma: no cover
    _quote = None
    Request = None
    urlopen = None

UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL") or os.getenv("REDIS_REST_URL") or os.getenv("UPSTASH_URL")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN") or os.getenv("REDIS_REST_TOKEN") or os.getenv("UPSTASH_TOKEN")
UPSTASH_KEY = os.getenv("XP_STORE_UPSTASH_KEY", "satpam:xp_store")

def _now_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def _project_store_path() -> Path:
    # Prefer explicit path
    env_path = os.getenv("XP_STORE_PATH")
    if env_path:
        p = Path(env_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    # Fallback common locations
    candidates = [
        Path("satpambot/bot/data/xp_store.json"),
        Path("./satpambot/bot/data/xp_store.json"),
        Path.cwd() / "satpambot" / "bot" / "data" / "xp_store.json",
    ]
    for p in candidates:
        parent = p if p.suffix else (p / "xp_store.json")
        if parent.parent.exists() or parent.parent.as_posix().endswith("/data"):
            parent.parent.mkdir(parents=True, exist_ok=True)
            return parent
    # Last resort
    p = Path.cwd() / "xp_store.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

LOCAL_STORE_PATH = _project_store_path()

def _upstash_get() -> Dict[str, Any] | None:
    if not (UPSTASH_URL and UPSTASH_TOKEN and _quote and Request):
        return None
    url = f"{UPSTASH_URL.rstrip('/')}/get/{_quote(UPSTASH_KEY)}"
    req = Request(url, headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"})
    with urlopen(req, timeout=5) as resp:
        raw = resp.read().decode("utf-8")
    try:
        payload = json.loads(raw)
        val = payload.get("result")
        if isinstance(val, str):
            return json.loads(val)
        return val
    except Exception:
        return None

def _upstash_set(data: Dict[str, Any]) -> bool:
    if not (UPSTASH_URL and UPSTASH_TOKEN and _quote and Request):
        return False
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    url = f"{UPSTASH_URL.rstrip('/')}/set/{_quote(UPSTASH_KEY)}/{_quote(payload)}"
    req = Request(url, headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"})
    try:
        with urlopen(req, timeout=5) as resp:
            _ = resp.read()
        return True
    except Exception:
        return False

def _init_store() -> Dict[str, Any]:
    return {
        "version": 2,
        "users": {},
        "awards": [],
        "stats": {"total": 0},
        "updated_at": _now_iso(),
    }

def load_store() -> Dict[str, Any]:
    # Try Upstash first
    data = _upstash_get()
    if isinstance(data, dict) and "users" in data:
        return data
    # Fallback file
    p = LOCAL_STORE_PATH
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    data = _init_store()
    save_store(data)
    return data

def save_store(data: Dict[str, Any]) -> None:
    # Always update timestamp
    data["updated_at"] = _now_iso()
    # Write local file
    p = LOCAL_STORE_PATH
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    # Try Upstash mirror (best-effort)
    _upstash_set(data)

# ---- Monkey patch XPStore if needed ----
def _monkey_patch():
    try:
        from satpambot.bot.modules.discord_bot.services import xp_store as xs
    except Exception:
        xs = None

    if xs is None:
        return False

    # If module has class XPStore, ensure it has load/save; otherwise provide a shim object on the module
    patched = False
    if hasattr(xs, "XPStore"):
        XP = xs.XPStore
        if not hasattr(XP, "load"):
            @classmethod
            def _load(cls):
                return load_store()
            XP.load = _load  # type: ignore[attr-defined]
            patched = True
        if not hasattr(XP, "save"):
            @classmethod
            def _save(cls, data):
                return save_store(data)
            XP.save = _save  # type: ignore[attr-defined]
            patched = True
    else:
        class _XPStoreShim:  # very small surface area used by overlays
            @classmethod
            def load(cls):
                return load_store()
            @classmethod
            def save(cls, data):
                return save_store(data)
        setattr(xs, "XPStore", _XPStoreShim)
        patched = True
    return patched

class XPStoreCompatOverlay(commands.Cog):
    """Inject XPStore.load/save and provide Upstash/file backing."""
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    cog = XPStoreCompatOverlay(bot)
    bot.add_cog(cog)
    patched = _monkey_patch()
    src = "Upstash" if (UPSTASH_URL and UPSTASH_TOKEN) else "File"
    try:
        bot.logger.info("[xp_store_compat] ready (patched=%s, src=%s, path=%s)", patched, src, LOCAL_STORE_PATH)
    except Exception:
        print(f"[xp_store_compat] ready (patched={patched}, src={src}, path={LOCAL_STORE_PATH})")
