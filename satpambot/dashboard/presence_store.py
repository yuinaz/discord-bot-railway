
from __future__ import annotations
import json, os, time
from pathlib import Path
from typing import Dict, Any

DATA_DIR = Path("data"); DATA_DIR.mkdir(parents=True, exist_ok=True)
STORE = DATA_DIR / "presence_override.json"

DEFAULT = {"mode":"auto","status":"online","type":"playing","text":"","url":""}

def read_presence() -> Dict[str, Any]:
    if STORE.exists():
        try:
            return {**DEFAULT, **json.loads(STORE.read_text("utf-8"))}
        except Exception:
            return DEFAULT.copy()
    return DEFAULT.copy()

def write_presence(d: Dict[str, Any]) -> None:
    data = {**DEFAULT, **(d or {})}
    # sanitize
    data["mode"] = "manual" if str(data.get("mode","auto")).lower()=="manual" else "auto"
    st = str(data.get("status","online")).lower()
    data["status"] = st if st in ("online","idle","dnd","invisible") else "online"
    tp = str(data.get("type","playing")).lower()
    data["type"] = tp if tp in ("playing","listening","watching","competing","streaming") else "playing"
    data["text"] = str(data.get("text",""))[:128]
    data["url"] = str(data.get("url",""))[:256]
    tmp = STORE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), "utf-8")
    os.replace(tmp, STORE)
