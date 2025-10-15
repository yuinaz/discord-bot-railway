import re, sys
from pathlib import Path

TARGET = Path("satpambot/bot/modules/discord_bot/helpers/smoke_utils.py")
src = TARGET.read_text(encoding="utf-8")

checks = [
    r"\basync\s+def\s+wait_until_ready\s*\(",
    r"\bdef\s+get_channel\s*\(",
    r"@property\s*\ndef\s+guilds\s*\(",
    r"@property\s*\ndef\s+loop\s*\(",
    r"@property\s*\ndef\s+user\s*\(",
    r"\bdef\s+is_closed\s*\(",
    r"\basync\s+def\s+close\s*\(",
]

missing = [pat for pat in checks if not re.search(pat, src)]
if missing:
    print("[FAIL] Missing stubs:", missing)
    sys.exit(1)
print("OK — DummyBot has wait_until_ready and safe stubs.")
