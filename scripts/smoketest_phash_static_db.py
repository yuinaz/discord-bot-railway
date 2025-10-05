# -*- coding: utf-8 -*-
"""
smoketest_phash_static_db.py
----------------------------
Smoketest ringan untuk memverifikasi file:
  data/phash_static/SATPAMBOT_PHASH_DB_V1.json

- Cek struktur JSON (harus object dengan key "phash")
- Cek setiap pHash berupa string hex 16-char (64-bit)
- Print ringkasan jumlah & unique

Jalankan:
  python scripts/smoketest_phash_static_db.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _is_hex16(s: str) -> bool:
    return (
        isinstance(s, str)
        and len(s) == 16
        and all(c in "0123456789abcdef" for c in s.lower())
    )


def main() -> int:
    p = Path("data/phash_static/SATPAMBOT_PHASH_DB_V1.json")
    if not p.exists():
        print(f"[ERR] File tidak ditemukan: {p}")
        return 2

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERR] Gagal parse JSON: {e}")
        return 3

    if not isinstance(data, dict) or "phash" not in data:
        print("[ERR] Struktur salah. Harus object dengan key 'phash' (list).")
        return 4

    ph = data["phash"]
    if not isinstance(ph, list):
        print("[ERR] 'phash' harus list.")
        return 5

    bad = [h for h in ph if not _is_hex16(h)]
    if bad:
        print(f"[ERR] {len(bad)} entri tidak valid (contoh 5): {bad[:5]}")
        return 6

    total = len(ph)
    uniq = len(set(ph))
    if total != uniq:
        dup = total - uniq
        print(f"[WARN] Ada {dup} duplikat pHash (total={total}, unique={uniq}).")
    else:
        print(f"[OK] pHash total={total}, unique={uniq}.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
