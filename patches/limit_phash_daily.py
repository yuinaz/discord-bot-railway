#!/usr/bin/env python3
# patches/limit_phash_daily.py
from __future__ import annotations
import re, sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "cogs" / "anti_image_phash_runtime.py",
    ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "cogs" / "anti_image_phash_runtime_strict.py",
]

MARK_GLOBAL = "# DAILY LIMIT GLOBALS — auto-inserted"
MARK_BLOCK  = "# DAILY LIMIT — auto-inserted"
LOG_NEEDLE  = "pHash DB loaded from Discord"

def ensure_globals(s: str) -> str:
    if MARK_GLOBAL in s:
        return s
    # sisipkan globals setelah import block paling atas
    m = re.search(r'^(?:from\s+\S+\s+import\s+.*|import\s+\S+).*$',
                  s, re.M)
    insert_pos = 0
    if m:
        # lompat ke akhir seluruh blok import
        end = m.end()
        while True:
            nxt = re.search(r'^(?:from\s+\S+\s+import\s+.*|import\s+\S+).*$',
                            s[end:], re.M)
            if not nxt: break
            end += nxt.end()
        insert_pos = end

    block = f"""
{MARK_GLOBAL}
import time, os
_PHASH_REFRESH_SECONDS = int(os.getenv("PHASH_REFRESH_SECONDS", "86400"))  # default: 24 jam
_PHASH_LAST_REFRESH: dict[int, float] = {{}}
"""
    return s[:insert_pos] + ("\n" if insert_pos else "") + block.lstrip("\n") + s[insert_pos:]

def insert_guard_once(s: str) -> str:
    # cari semua baris log yang memuat needle
    for mlog in re.finditer(re.escape(LOG_NEEDLE), s):
        # cari header fungsi (async def ...) terdekat di atasnya
        defs = list(re.finditer(r'^([ \t]*)async\s+def\s+\w+\s*\([^)]*\)\s*:\s*$',
                                s[:mlog.start()], re.M))
        if not defs: 
            continue
        h = defs[-1]
        header_end = h.end()

        # Deteksi indent body (baris non-kosong pertama setelah header)
        m_first = re.search(r'^(?P<i>[ \t]+)\S', s[header_end:], re.M)
        if not m_first:
            continue
        body_indent = m_first.group('i')

        # Pastikan guard belum ada di body fungsi ini
        next_def = re.search(r'^[ \t]*async\s+def\s+\w+\s*\(|^[ \t]*class\s+\w+\s*\(',
                             s[header_end:], re.M)
        body_end = header_end + (next_def.start() if next_def else len(s) - header_end)
        if MARK_BLOCK in s[header_end:body_end]:
            continue

        guard = (
            f"{body_indent}{MARK_BLOCK}\n"
            f"{body_indent}# Batasi reload pHash: maksimal sekali setiap _PHASH_REFRESH_SECONDS per guild\n"
            f"{body_indent}gid = int(getattr(locals().get('guild', None), 'id', 0) or 0)\n"
            f"{body_indent}if gid:\n"
            f"{body_indent}    last = _PHASH_LAST_REFRESH.get(gid, 0.0)\n"
            f"{body_indent}    now = time.time()\n"
            f"{body_indent}    if now - last < _PHASH_REFRESH_SECONDS:\n"
            f"{body_indent}        return  # sudah refresh baru-baru ini — skip untuk cegah spam/log\n"
            f"{body_indent}    _PHASH_LAST_REFRESH[gid] = now\n"
        )

        # sisipkan tepat di awal body
        s = s[:header_end] + guard + s[header_end:]
        # cukup sekali per fungsi yang mengeluarkan log
        break
    return s

def process_file(p: Path) -> bool:
    if not p.exists():
        print(f"[SKIP] {p} (not found)")
        return False
    src = p.read_text(encoding="utf-8")
    before = src

    src = ensure_globals(src)
    # sisipkan guard pada fungsi yang memuat log "pHash DB loaded from Discord"
    if LOG_NEEDLE in src:
        src = insert_guard_once(src)

    changed = (src != before)
    if changed:
        p.write_text(src, encoding="utf-8", newline="\n")
        print(f"[OK] Patched: {p.relative_to(ROOT)}")
    else:
        print(f"[OK] No change needed: {p.relative_to(ROOT)}")
    return changed

def main() -> int:
    any_changed = False
    for t in TARGETS:
        if process_file(t):
            any_changed = True
    if any_changed:
        print("[TIP] Jalankan: python scripts/smoke_all.py")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
