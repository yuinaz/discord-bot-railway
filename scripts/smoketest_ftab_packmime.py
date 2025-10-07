#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smoketest PackMime STRICT
- import modul
- validasi ringan config first_touch_autoban_pack_mime.json
Exit 0 = OK, 1 = FAIL
"""
import importlib, json, os, sys, traceback

MOD = "satpambot.bot.modules.discord_bot.cogs.first_touch_autoban_pack_mime"
CFG_REL = os.path.join("config", "first_touch_autoban_pack_mime.json")

def add_root():
    here = os.path.abspath(os.path.dirname(__file__))
    root = os.path.abspath(os.path.join(here, ".."))
    if root not in sys.path: sys.path.insert(0, root)
    return root

def ok(m): print(f"OK   : {m}")
def warn(m): print(f"WARN : {m}")
def fail(m): print(f"FAIL : {m}")

def check_import():
    try:
        mod = importlib.import_module(MOD)
        if getattr(mod, "FirstTouchAutoBanPackMime", None) is None:
            fail("Class FirstTouchAutoBanPackMime tidak ditemukan")
            return False
        ok(f"import OK: {MOD}")
        return True
    except Exception as e:
        fail(f"import error: {MOD} :: {e}")
        traceback.print_exc()
        return False

def check_config(cfg_path):
    if not os.path.exists(cfg_path):
        warn(f"config tidak ditemukan (skip): {cfg_path}")
        return True
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        fail(f"config bukan JSON valid: {e}")
        return False

    must_bools = ["enabled","exempt_threads","only_roleless","pattern_pack_allow_image_prefix","require_consecutive_numbers"]
    for k in must_bools:
        if k in cfg and not isinstance(cfg[k], bool):
            fail(f"config.{k} harus bool"); return False

    must_ints = ["pattern_pack_min_attachments","mime_direct_ban_min_mismatches","delete_message_days","log_channel_id"]
    for k in must_ints:
        if k in cfg and not isinstance(cfg[k], int):
            fail(f"config.{k} harus int"); return False

    for k in ["pattern_pack_exts","image_kinds"]:
        if k in cfg and not isinstance(cfg[k], list):
            fail(f"config.{k} harus list"); return False

    ok(f"config OK: {cfg_path}")
    return True

def main():
    root = add_root()
    all_ok = check_import() and check_config(os.path.join(root, CFG_REL))
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
