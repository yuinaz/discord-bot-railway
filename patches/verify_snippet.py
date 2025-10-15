# -*- coding: utf-8 -*-
"""
Verifier — checks presence of expected methods on DummyBot/_DummyBot
for both helper and scripts smoke_utils modules (if available).
"""
import importlib, sys, types, os
from pathlib import Path
import importlib.util as iutil

def _import_by_path(modname: str, filepath: Path):
    spec = iutil.spec_from_file_location(modname, str(filepath))
    if spec and spec.loader:
        mod = iutil.module_from_spec(spec)
        sys.modules[modname] = mod
        spec.loader.exec_module(mod)
        return mod
    return None

def _check_module(mod, label):
    ok = True
    cls = getattr(mod, "DummyBot", None)
    alias = hasattr(mod, "_DummyBot")
    print(f"[{label}] has DummyBot? {bool(cls)}  _DummyBot alias? {alias}")
    for target in filter(None, [cls, getattr(mod, "_DummyBot", None)]):
        name = f"{label}.{target.__name__}"
        for attr, is_async in [
            ("wait_until_ready", True),
            ("get_all_channels", False),
            ("get_channel", False),
            ("get_user", False),
            ("fetch_user", True),
        ]:
            has = hasattr(target, attr)
            print(f"  {name}.{attr:<18}: {has}")
            ok &= has
    return ok

def main():
    overall = True
    # 1) satpambot helper module
    try:
        helper = importlib.import_module("satpambot.bot.modules.discord_bot.helpers.smoke_utils")
        overall &= _check_module(helper, "helper")
    except Exception as e:
        print(f"[helper] import failed: {e}")
        overall = False

    # 2) scripts/smoke_utils.py (by path if import fails as package)
    script_path = Path("scripts") / "smoke_utils.py"
    if script_path.exists():
        try:
            scripts_mod = _import_by_path("scripts_smoke_utils_local", script_path)
            overall &= _check_module(scripts_mod, "scripts")
        except Exception as e:
            print(f"[scripts] import failed: {e}")
            overall = False
    else:
        print("[scripts] scripts/smoke_utils.py not found — skip")

    print("\n[OK]" if overall else "\n[WARN] Some checks failed")
if __name__ == "__main__":
    main()
