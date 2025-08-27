
from __future__ import annotations
import os, re, json, logging
from pathlib import Path
from typing import Dict, List, Tuple

log = logging.getLogger(__name__)

BASE = Path(__file__).resolve().parents[5]  # repo root

def _read_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _read_txt(p: Path) -> List[str]:
    try:
        lines = [x.strip() for x in p.read_text(encoding="utf-8", errors="ignore").splitlines()]
        return [x for x in lines if x and not x.startswith("#")]
    except Exception:
        return []

def _split_domains_patterns(lines: List[str]) -> Tuple[List[str], List[str]]:
    domains, patterns = [], []
    for s in lines:
        s_l = (s or "").lower()
        if re.search(r"[a-z0-9-]+\.[a-z]{2,}", s_l):
            domains.append(s_l)
        else:
            patterns.append(s)
    return sorted(set(domains)), sorted(set(patterns))

def load_whitelist_blacklist() -> Dict[str, List[str]]:
    # prefer JSON, fallback to TXT, then merge
    repo = BASE
    wl_json = repo / "satpambot/data/whitelist.json"
    bl_json = repo / "satpambot/data/blacklist.json"
    wl_txt = repo / "whitelist.txt"
    bl_txt = repo / "blacklist.txt"
    wl = _read_json(wl_json)
    bl = _read_json(bl_json)
    if not wl:
        d,p = _split_domains_patterns(_read_txt(wl_txt))
        wl = {"domains": d, "patterns": p}
    if not bl:
        d,p = _split_domains_patterns(_read_txt(bl_txt))
        bl = {"domains": d, "patterns": p}
    # ensure types
    wl_domains = [str(x).lower().strip() for x in (wl.get("domains") or []) if x]
    wl_patterns = [str(x).strip() for x in (wl.get("patterns") or []) if x]
    bl_domains = [str(x).lower().strip() for x in (bl.get("domains") or []) if x]
    bl_patterns = [str(x).strip() for x in (bl.get("patterns") or []) if x]
    return {
        "wl_domains": sorted(set(wl_domains)),
        "wl_patterns": wl_patterns,
        "bl_domains": sorted(set(bl_domains)),
        "bl_patterns": bl_patterns,
    }


def save_lists(wl_domains, wl_patterns, bl_domains, bl_patterns, repo_root: Path = None) -> bool:
    try:
        repo = repo_root or BASE
        data_dir = repo / "satpambot" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "whitelist.json").write_text(json.dumps({
            "domains": sorted(set([str(x).lower().strip() for x in wl_domains])),
            "patterns": [str(x).strip() for x in wl_patterns]
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        (data_dir / "blacklist.json").write_text(json.dumps({
            "domains": sorted(set([str(x).lower().strip() for x in bl_domains])),
            "patterns": [str(x).strip() for x in bl_patterns]
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False
