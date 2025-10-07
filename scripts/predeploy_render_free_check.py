#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Predeploy check for Render (Free plan friendly)
- Recommends python 3.11.x via runtime.txt
- Checks critical files and light deps
- No config modifications
"""
import os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
def abspath(*p): return os.path.abspath(os.path.join(ROOT, *p))

def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

def has(path): return os.path.exists(path)

def main() -> int:
    rc = 0
    # runtime.txt
    rtp = abspath("runtime.txt")
    if has(rtp):
        txt = read_text(rtp).strip()
        print(f"OK   : runtime.txt -> {txt}")
        if not txt.startswith("python-3.11"):
            print("WARN : Disarankan python-3.11.x untuk build cepat & stabil di Render.")
    else:
        print("WARN : runtime.txt tidak ada; Render akan pakai default (3.13). Pertimbangkan tambah 'python-3.11.9'.")

    # requirements sanity
    reqp = abspath("requirements.txt")
    if has(reqp):
        req = read_text(reqp)
        if "gunicorn" not in req:
            print("WARN : 'gunicorn' tidak terdeteksi di requirements.txt (disarankan untuk web server).")
        if "numpy" not in req:
            print("WARN : 'numpy' tidak terdeteksi — ok jika tidak digunakan, jika perlu pastikan versi kompatibel.")
        else:
            m = re.search(r"numpy\s*([<>=!~]=?[^\n]+)?", req, re.IGNORECASE)
            pin = m.group(0).strip() if m else "numpy"
            print(f"OK   : {pin}")
    else:
        print("WARN : requirements.txt tidak ditemukan di root.")

    # build script
    bsh = abspath("scripts", "build_render.sh")
    if has(bsh):
        print("OK   : scripts/build_render.sh ada")
    else:
        print("WARN : scripts/build_render.sh tidak ditemukan")

    # critical configs
    must_cfg = [
        ("config/first_touch_attachment_ban.json", True),
        ("config/first_touch_autoban_pack_mime.json", True),
        ("config/presence_mood_rotator.json", True),
    ]
    for rel, required in must_cfg:
        p = abspath(rel)
        if has(p):
            print(f"OK   : {rel}")
        else:
            lev = "FAIL" if required else "WARN"
            print(f"{lev} : {rel} tidak ada")
            if required: rc = 1

    # cogs existence (optional check)
    cogs = [
        "satpambot/bot/modules/discord_bot/cogs/first_touch_attachment_ban.py",
        "satpambot/bot/modules/discord_bot/cogs/first_touch_autoban_pack_mime.py",
        "satpambot/bot/modules/discord_bot/cogs/presence_mood_rotator.py",
        "satpambot/bot/modules/discord_bot/cogs/self_heal_runtime.py",
    ]
    for rel in cogs:
        p = abspath(rel)
        if has(p):
            print(f"OK   : {rel}")
        else:
            print(f"WARN : {rel} tidak ada")

    # env hints (cannot read Render env here)
    print("INFO : Pastikan di Render env: DISCORD_TOKEN, OPENAI-KEY/OPENAI_API_KEY (opsional), LOG_CHANNEL_ID_RAW.")
    return rc

if __name__ == "__main__":
    raise SystemExit(main())
