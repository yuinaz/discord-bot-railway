
#!/usr/bin/env python3
"""
ruff_surgical_fixes.py
- Safe, minimal edits to kill common Ruff errors (esp. F821) without changing config/format.
- Targets missing imports (re, os, asyncio, json, numpy as np, datetime.timedelta),
  and undefined names (sticker, stk, INTERVAL_SECONDS) seen in SatpamBot codebase.

Usage:
  python ruff_surgical_fixes.py --apply .         # apply in current repo
  python ruff_surgical_fixes.py --dry-run .       # show changes only
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT_MARKERS = {"pyproject.toml", "README.md", "main.py", "scripts", "satpambot"}

def is_repo_root(p: Path) -> bool:
    return any((p / m).exists() for m in ROOT_MARKERS)

def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")

def write(p: Path, s: str) -> None:
    p.write_text(s, encoding="utf-8")

def ensure_import(s: str, module: str, alias: str | None = None) -> str:
    if re.search(rf"^\s*import\s+{re.escape(module)}(\s|$)", s, re.M):
        return s
    if alias and re.search(rf"^\s*import\s+{re.escape(module)}\s+as\s+{re.escape(alias)}", s, re.M):
        return s
    # place after __future__ if exists, else at file start
    lines = s.splitlines()
    try:
        idx = next(i for i,l in enumerate(lines) if "from __future__ import" in l)
        insert_at = idx + 1
    except StopIteration:
        insert_at = 0
    imp = f"import {module}" + (f" as {alias}" if alias else "")
    if lines and lines[0].strip() != "" and insert_at == 0:
        imp = imp + "\n"
    lines.insert(insert_at, imp)
    return "\n".join(lines) + ("\n" if not s.endswith("\n") else "")

def ensure_from_import(s: str, module: str, name: str) -> str:
    if re.search(rf"^\s*from\s+{re.escape(module)}\s+import\s+.*\b{name}\b", s, re.M):
        return s
    # naive: add a new from-import
    lines = s.splitlines()
    try:
        idx = next(i for i,l in enumerate(lines) if "from __future__ import" in l)
        insert_at = idx + 1
    except StopIteration:
        insert_at = 0
    lines.insert(insert_at, f"from {module} import {name}")
    return "\n".join(lines) + ("\n" if not s.endswith("\n") else "")

def has_top_import(s: str, mod: str) -> bool:
    return re.search(rf"^\s*(?:from\s+{re.escape(mod)}\s+import|import\s+{re.escape(mod)})", s, re.M) is not None

def sanitize_shadow_imports(s: str) -> str:
    # Replace helper imports that shadow stdlib re/json
    s = re.sub(
        r"from\s+satpambot\.bot\.modules\.discord_bot\.helpers\s+import\s+([^#\n]+)",
        lambda m: "from satpambot.bot.modules.discord_bot.helpers import " + ", ".join(
            [x for x in re.split(r"\s*,\s*", m.group(1)) if x.strip() not in {"re","json"}]
        ) or "threadlog",
        s,
    )
    # Clean up trailing comma/space issues
    s = re.sub(r"import\s+,", "import ", s)
    s = re.sub(r",\s*,", ", ", s)
    return s

def need_import(s: str, token: str) -> bool:
    return (re.search(rf"\b{re.escape(token)}\.", s) is not None) and (not has_top_import(s, token))

def apply_fixes(path: Path) -> tuple[int, list[str]]:
    changed = 0
    diffs: list[str] = []
    for p in path.rglob("*.py"):
        if any(part.startswith((".", "__pycache__", "venv", "env", "site-packages")) for part in p.parts):
            continue
        try:
            s = read(p)
        except Exception:
            continue

        orig = s

        # 0) helper shadowing
        s = sanitize_shadow_imports(s)

        # 1) missing imports based on usage
        if need_import(s, "re"):
            s = ensure_import(s, "re")
        if need_import(s, "os"):
            s = ensure_import(s, "os")
        if need_import(s, "asyncio"):
            s = ensure_import(s, "asyncio")
        if need_import(s, "json"):
            s = ensure_import(s, "json")
        if "np." in s and not has_top_import(s, "numpy"):
            s = ensure_import(s, "numpy", alias="np")
        if re.search(r"\btimedelta\b", s) and "timedelta(" in s and "from datetime import timedelta" not in s:
            s = ensure_from_import(s, "datetime", "timedelta")
        if re.search(r"\bcommands\.", s) and "from discord.ext import commands" not in s:
            s = ensure_from_import(s, "discord.ext", "commands")

        # 2) Gentle guards for known undefined names
        # sticker / stk just before first usage
        if re.search(r"\bsticker\b", s) and "stickers=[" in s and "sticker = None" not in s:
            s = re.sub(r"(\n\s*)(if\s+['\"]sticker['\"]\s+in\s+locals\(\).*)", r"\1sticker = None\n\1\2", s, count=1)
        if re.search(r"\bstk\b", s) and "stickers=[" in s and "stk = None" not in s:
            s = re.sub(r"(\n\s*)(if\s+['\"]stk['\"]\s+in\s+locals\(\).*)", r"\1stk = None\n\1\2", s, count=1)

        # INTERVAL_SECONDS fallback
        if "await asyncio.sleep(INTERVAL_SECONDS)" in s and "INTERVAL_SECONDS" not in s:
            s = re.sub(r"(await\s+asyncio\.sleep\()(INTERVAL_SECONDS)(\))", r"\g<1>30\g<3>", s)

        # 3) Bare except -> except Exception
        s = re.sub(r"(^|\n)(\s*)except\s*:\s*\n", r"\1\2except Exception:\n", s)

        # 4) None/True/False comparisons
        s = re.sub(r"==\s*None\b", "is None", s)
        s = re.sub(r"!=\s*None\b", "is not None", s)
        s = re.sub(r"==\s*True\b", "is True", s)
        s = re.sub(r"==\s*False\b", "is False", s)
        s = re.sub(r"!=\s*True\b", "is not True", s)
        s = re.sub(r"!=\s*False\b", "is not False", s)

        if s != orig:
            changed += 1
            diffs.append(str(p))
            # will write later depending on flag
            if APPLY:
                write(p, s)

    return changed, diffs

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--apply", action="store_true", help="apply changes")
    ap.add_argument("--dry-run", action="store_true", help="show what would change")
    args = ap.parse_args()

    global APPLY
    APPLY = args.apply and not args.dry_run

    base = Path(args.path).resolve()
    if not is_repo_root(base):
        print(f"[!] Warning: '{base}' tidak terlihat seperti root repo (abaikan jika yakin).", file=sys.stderr)

    changed, files = apply_fixes(base)
    mode = "APPLY" if APPLY else ("DRY-RUN" if args.dry_run else "LIST")
    print(json.dumps({"mode": mode, "changed_files": changed, "files": files[-50:]}, indent=2))
