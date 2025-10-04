#!/usr/bin/env python3
"""
patches/limit_phash_daily_v2.py

Tujuan:
- Tambahkan helper _phash_daily_gate() (idempotent).
- Pastikan ada pemanggilan gate tepat SEBELUM log:
    "pHash DB loaded from Discord"
- Tidak menghapus guard inline kamu yang sudah ada;
  ini cuma menambah gate ringan agar checker & anti-spam aman.

File target:
- satpambot/bot/modules/discord_bot/cogs/anti_image_phash_runtime.py
- satpambot/bot/modules/discord_bot/cogs/anti_image_phash_runtime_strict.py
"""

from __future__ import annotations
import re, sys
from pathlib import Path

FILES = [
    Path("satpambot/bot/modules/discord_bot/cogs/anti_image_phash_runtime.py"),
    Path("satpambot/bot/modules/discord_bot/cogs/anti_image_phash_runtime_strict.py"),
]

HDR_HELPER = """
# === pHash daily gate helper (auto-inserted) ===
try:
    _PHASH_REFRESH_SECONDS
except NameError:
    import os
    _PHASH_REFRESH_SECONDS = int(os.getenv("PHASH_REFRESH_SECONDS", "86400"))  # default: 24 jam

try:
    _PHASH_LAST
except NameError:
    _PHASH_LAST = {}

def _phash_daily_gate(guild_id: int):
    try:
        import time
        now = time.time()
    except Exception:
        return True  # fallback: jangan blok
    last = _PHASH_LAST.get(guild_id, 0.0)
    if now - last < _PHASH_REFRESH_SECONDS:
        return False
    _PHASH_LAST[guild_id] = now
    return True
# === end helper ===
""".lstrip()

def ensure_helper(src: str) -> str:
    if "_phash_daily_gate(" in src and "_PHASH_REFRESH_SECONDS" in src:
        return src  # sudah ada
    # sisipkan helper setelah import teratas (atau paling atas file)
    m = re.search(r"^(?:from\s+\S+\s+import\s+.*|import\s+\S+).*?$", src, flags=re.M)
    insert_pos = 0
    last = 0
    for mm in re.finditer(r"^(?:from\s+\S+\s+import\s+.*|import\s+\S+).*?$", src, flags=re.M):
        last = mm.end()
    insert_pos = last if last else 0
    return src[:insert_pos] + ("\n\n" if insert_pos else "") + HDR_HELPER + src[insert_pos:]

def add_gate_before_log(src: str) -> str:
    # Cari baris log
    log_pat = re.compile(r'^[ \t]*await\s+self\._log\(.*pHash DB loaded from Discord.*$', re.M)
    m = log_pat.search(src)
    if not m:
        return src  # tidak ketemu log -> biarkan
    # Dapatkan indent dari baris log
    line = m.group(0)
    indent = re.match(r'^([ \t]*)', line).group(1)
    # Jika dalam 10 baris sebelumnya sudah ada _phash_daily_gate -> skip
    start_idx = max(0, src.rfind("\n", 0, m.start()))
    pre = src[start_idx:m.start()]
    if "_phash_daily_gate(" in pre[-600:]:  # window kecil sebelum log
        return src

    gate_block = (
        f"{indent}# pHash daily gate (auto-inserted)\n"
        f"{indent}try:\n"
        f"{indent}    gid = int(getattr(guild, 'id', getattr(getattr(locals().get('msg', None), 'guild', None), 'id', 0)) or 0)\n"
        f"{indent}except Exception:\n"
        f"{indent}    gid = 0\n"
        f"{indent}if not _phash_daily_gate(gid):\n"
        f"{indent}    return\n"
    )

    # sisipkan gate_block tepat sebelum baris log
    return src[:m.start()] + gate_block + src[m.start():]

def main() -> int:
    changed = 0
    for p in FILES:
        if not p.exists():
            print(f"[SKIP] {p} (not found)")
            continue
        s = p.read_text(encoding="utf-8", errors="ignore")
        orig = s
        s = ensure_helper(s)
        s = add_gate_before_log(s)
        if s != orig:
            p.write_text(s, encoding="utf-8", newline="\n")
            print(f"[OK] Patched: {p}")
            changed += 1
        else:
            print(f"[OK] No changes needed: {p}")
    if changed == 0:
        print("[INFO] Nothing to change (already ok).")
    print("[TIP] Jalankan: python scripts/smoke_all.py")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
