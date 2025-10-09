#!/usr/bin/env python3
"""
verify_snippet.py
Cek apakah DummyBot sudah punya async wait_until_ready().
"""
import os, re, sys

path = os.path.join("satpambot","bot","modules","discord_bot","helpers","smoke_utils.py")
if len(sys.argv) > 1:
    path = sys.argv[1]

if not os.path.exists(path):
    print("NOT FOUND:", path)
    sys.exit(2)

src = open(path, "r", encoding="utf-8").read()
if re.search(r"class\s+DummyBot\b", src) and re.search(r"^\s*async\s+def\s+wait_until_ready\s*\(", src, flags=re.M):
    print("OK: DummyBot.wait_until_ready() ditemukan di", path)
    sys.exit(0)
else:
    print("MISSING: async wait_until_ready() di", path)
    sys.exit(1)
