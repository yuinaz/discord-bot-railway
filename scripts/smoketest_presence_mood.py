#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smoketest PresenceMoodRotator
--------------------------------
Cek cepat:
1) Struktur repo & PYTHONPATH (inject root otomatis).
2) Import modul: satpambot.bot.modules.discord_bot.cogs.presence_mood_rotator
3) Validasi ringan config: config/presence_mood_rotator.json
   - interval_minutes (int)
   - default_status (str)
   - moods (dict of list[{type,name}])
Exit code 0 = OK, 1 = FAIL.
"""

import importlib
import json
import os
import sys
import traceback

MOD = "satpambot.bot.modules.discord_bot.cogs.presence_mood_rotator"
CFG_REL = os.path.join("config", "presence_mood_rotator.json")


def add_root_to_sys_path():
    """Tambahkan root repo (parent dari folder scripts/) ke sys.path."""
    here = os.path.abspath(os.path.dirname(__file__))
    root = os.path.abspath(os.path.join(here, ".."))
    if root not in sys.path:
        sys.path.insert(0, root)
    return root


def ok(msg):  # print OK line
    print(f"OK   : {msg}")


def warn(msg):
    print(f"WARN : {msg}")


def fail(msg):
    print(f"FAIL : {msg}")


def validate_config(cfg_path):
    """Validasi ringan untuk presence_mood_rotator.json."""
    if not os.path.exists(cfg_path):
        warn(f"config tidak ditemukan (skip): {cfg_path}")
        return True  # tidak wajib ada

    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        fail(f"config tidak valid JSON: {cfg_path} :: {e}")
        return False

    # interval_minutes
    val = data.get("interval_minutes", 120)
    if not isinstance(val, int):
        fail("config.interval_minutes harus int")
        return False

    # default_status
    val = data.get("default_status", "online")
    if not isinstance(val, str):
        fail("config.default_status harus string")
        return False

    # moods
    moods = data.get("moods", {})
    if not isinstance(moods, dict):
        fail("config.moods harus dict")
        return False

    # validasi item dasar tiap mood (opsional tapi membantu)
    def _check_bucket(name, arr):
        if not isinstance(arr, list):
            fail(f"config.moods['{name}'] harus list")
            return False
        for i, it in enumerate(arr):
            if not isinstance(it, dict):
                fail(f"config.moods['{name}'][{i}] harus object {{type,name}}")
                return False
            if "type" not in it or "name" not in it:
                fail(f"config.moods['{name}'][{i}] wajib punya key 'type' & 'name'")
                return False
        return True

    ok_bucket = True
    for bucket_name, bucket in moods.items():
        if bucket is None:
            continue
        ok_bucket = _check_bucket(bucket_name, bucket) and ok_bucket

    if not ok_bucket:
        return False

    ok(f"config OK: {cfg_path}")
    return True


def check_import(modname):
    """Pastikan modul bisa di-import dan kelas PresenceMoodRotator ada."""
    try:
        mod = importlib.import_module(modname)
    except Exception as e:
        fail(f"import error: {modname}\n{e}")
        traceback.print_exc()
        return False

    # kelas PresenceMoodRotator harus ada
    cog = getattr(mod, "PresenceMoodRotator", None)
    if cog is None:
        fail("PresenceMoodRotator tidak ditemukan di modul")
        return False

    ok(f"import OK: {modname} (PresenceMoodRotator ditemukan)")
    return True


def main():
    root = add_root_to_sys_path()

    # cek struktur minimal
    pkg_root = os.path.join(root, "satpambot")
    if not os.path.isdir(pkg_root):
        warn(f"folder 'satpambot' tidak ditemukan di root: {root}")
        warn("pastikan menjalankan dari root repo SatpamBot (yang ada folder 'satpambot', 'scripts', 'config')")
        # lanjut saja; kalau import gagal, akan ketahuan

    all_ok = True
    all_ok &= check_import(MOD)
    all_ok &= validate_config(os.path.join(root, CFG_REL))

    if all_ok:
        ok("Smoketest PresenceMoodRotator PASSED")
        sys.exit(0)
    else:
        fail("Smoketest PresenceMoodRotator FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
