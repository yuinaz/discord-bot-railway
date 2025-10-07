# Offline-friendly smoke test to verify imports only.
# Ensures repository root is on sys.path so `satpambot` package can be found.

import sys, pathlib, importlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def _try(modname: str) -> None:
    try:
        importlib.import_module(modname)
        print(f"[OK] {modname}: import ok")
    except Exception as e:
        print(f"[FAIL] {modname}: {e}")

_try("satpambot.utils.translate_utils")
_try("satpambot.bot.modules.discord_bot.cogs.translator")

print("-- OK if both above show [OK]")
