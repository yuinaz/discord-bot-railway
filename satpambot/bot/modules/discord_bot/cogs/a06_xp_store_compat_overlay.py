import os, json, time, logging, pathlib, urllib.request, urllib.parse
from typing import Any, Dict

log = logging.getLogger(__name__)

try:
    from satpambot.bot.modules.discord_bot.services.xp_store import XPStore  # type: ignore
except Exception as e:
    XPStore = None  # type: ignore
    log.exception("[xp_store_compat] cannot import XPStore: %s", e)

DEFAULT = {"version": 2, "users": {}, "awards": {}, "stats": {}, "updated_at": 0}
DEFAULT_PATH = pathlib.Path("satpambot/bot/data/xp_store.json")

class _UpstashKV:
    def __init__(self, url: str, token: str, prefix: str = "satpambot"):
        self.url = url.rstrip("/")
        self.token = token
        self.prefix = prefix

    def _fetch(self, path: str) -> Dict[str, Any]:
        req = urllib.request.Request(self.url + path)
        req.add_header("Authorization", f"Bearer {self.token}")
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read().decode("utf-8")
            try:
                return json.loads(data)
            except Exception:
                return {"error": "decode", "raw": data}

    def get(self, key: str):
        k = f"{self.prefix}:{key}"
        path = "/get/" + urllib.parse.quote(k, safe="")
        return self._fetch(path).get("result")

    def set(self, key: str, value: str) -> bool:
        k = f"{self.prefix}:{key}"
        v = urllib.parse.quote(value, safe="")
        path = "/set/" + urllib.parse.quote(k, safe="") + "/" + v
        res = self._fetch(path)
        return res.get("result") == "OK"

def _ensure_dir(p: pathlib.Path):
    p.parent.mkdir(parents=True, exist_ok=True)

def _file_load(path: pathlib.Path):
    if not path.exists():
        _ensure_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT, f, ensure_ascii=False, indent=2)
        return DEFAULT.copy()
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception as e:
            log.warning("[xp_store_compat] invalid json at %s: %s; resetting.", path, e)
            with open(path, "w", encoding="utf-8") as fw:
                json.dump(DEFAULT, fw, ensure_ascii=False, indent=2)
            return DEFAULT.copy()

def _file_save(data: Dict[str, Any], path: pathlib.Path):
    _ensure_dir(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)

def _upstash_backend():
    url = os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if url and token:
        return _UpstashKV(url, token, prefix=os.environ.get("UPSTASH_PREFIX", "satpambot"))
    return None

def _load_impl(path: str = None):
    ub = _upstash_backend()
    if ub:
        raw = ub.get("xp_store")
        if not raw:
            data = DEFAULT.copy()
            data["updated_at"] = int(time.time())
            ub.set("xp_store", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
            log.info("[xp_store_compat] created default Upstash value for xp_store")
            return data
        try:
            return json.loads(raw)
        except Exception as e:
            log.warning("[xp_store_compat] Upstash decode failed: %s; resetting default.", e)
            data = DEFAULT.copy()
            data["updated_at"] = int(time.time())
            ub.set("xp_store", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
            return data
    # file mode
    the_path = pathlib.Path(path) if path else DEFAULT_PATH
    return _file_load(the_path)

def _save_impl(data: Dict[str, Any], path: str = None):
    data = dict(data or {})
    data.setdefault("version", 2)
    data.setdefault("users", {})
    data.setdefault("awards", {})
    data.setdefault("stats", {})
    data["updated_at"] = int(time.time())
    ub = _upstash_backend()
    if ub:
        ok = ub.set("xp_store", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        if not ok:
            log.warning("[xp_store_compat] Upstash set failed; falling back to file.")
    # Always keep a file copy as local cache/snapshot
    the_path = pathlib.Path(path) if path else DEFAULT_PATH
    try:
        _file_save(data, the_path)
    except Exception as e:
        log.warning("[xp_store_compat] file save failed at %s: %s", the_path, e)
    return True

async def setup(bot):
    # Inject compat methods once at import/setup
    if XPStore is None:
        log.error("[xp_store_compat] XPStore not available; cannot inject.")
        return
    injected = []
    if not hasattr(XPStore, "load") or not callable(getattr(XPStore, "load")):
        def _load(cls, path=None):
            return _load_impl(path)
        XPStore.load = classmethod(_load)  # type: ignore
        injected.append("load")
    if not hasattr(XPStore, "save") or not callable(getattr(XPStore, "save")):
        def _save(cls, data, path=None):
            return _save_impl(data, path)
        XPStore.save = classmethod(_save)  # type: ignore
        injected.append("save")
    if injected:
        log.info("[xp_store_compat] injected methods: %s (Upstash=%s)", ", ".join(injected), bool(_upstash_backend()))
    else:
        log.info("[xp_store_compat] no-op (methods already present) (Upstash=%s)", bool(_upstash_backend()))
