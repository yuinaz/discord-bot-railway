
from __future__ import annotations
import os, json, re
from pathlib import Path
from typing import Set, Tuple

# Try common roots (repo or installed package layout)
ROOT_HINTS = [
    Path("."),
    Path(__file__).resolve().parents[5] if len(Path(__file__).resolve().parents) >= 5 else Path("."),
]

LIST_CANDIDATES = [
    ("whitelist.json", "json"),
    ("blacklist.json", "json"),
    ("whitelist.txt", "txt"),
    ("blacklist.txt", "txt"),
    ("satpambot/lists/whitelist.json", "json"),
    ("satpambot/lists/blacklist.json", "json"),
    ("satpambot/lists/whitelist.txt", "txt"),
    ("satpambot/lists/blacklist.txt", "txt"),
]

def _read_file(p: Path, kind: str) -> Set[str]:
    try:
        s = p.read_text(encoding="utf-8", errors="ignore")
        if kind == "json":
            data = json.loads(s)
            if isinstance(data, list):
                return {str(x).strip().lower() for x in data if str(x).strip()}
            if isinstance(data, dict):
                out = set()
                for v in data.values():
                    if isinstance(v, list):
                        for x in v:
                            x = str(x).strip().lower()
                            if x:
                                out.add(x)
                return out
            return set()
        # txt
        out = set()
        for line in s.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            out.add(line.lower())
        return out
    except Exception:
        return set()

def _normalize_host(h: str) -> str:
    h = h.strip().lower()
    h = re.sub(r"^https?://", "", h)
    h = h.split("/")[0]
    return h

def load_lists() -> Tuple[Set[str], Set[str], Set[str], Set[str]]:
    """Return (whitelist_hosts, blacklist_hosts, soft_domains, soft_keywords)."""
    wl, bl = set(), set()
    for base in ROOT_HINTS:
        for name, kind in LIST_CANDIDATES:
            p = (base / name)
            if p.exists():
                items = _read_file(p, kind)
                if "white" in name:
                    wl |= items
                else:
                    bl |= items
    wl = {_normalize_host(x) for x in wl}
    bl = {_normalize_host(x) for x in bl}
    # ENV soft allow domains
    soft_domains = set()
    for key in ["NSFW_SOFT_DOMAINS", "NSFW_SOFT_FORUM_NAMES"]:
        val = os.getenv(key, "")
        for part in val.split(","):
            part = part.strip().lower()
            if part:
                soft_domains.add(_normalize_host(part))
    # ENV soft keywords
    soft_keywords = set()
    val = os.getenv("NSFW_SOFT_KEYWORDS", "")
    for part in val.split(","):
        part = part.strip().lower()
        if part:
            soft_keywords.add(part)
    return wl, bl, soft_domains, soft_keywords

def url_to_host(url: str) -> str:
    u = url.strip().lower()
    u = re.sub(r"^<|>$", "", u)  # strip Discord <> autolink
    u = re.sub(r"^https?://", "", u)
    return u.split("/")[0]
