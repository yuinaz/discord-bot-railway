# Patch to disable ONLY the '⚠️' warning reaction while keeping self-learning logic.
# Usage: py -3.10 scripts/hotfix_self_learning_nowarn.py
import os, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
candidates = [
    ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "cogs" / "self_learning_guard.py",
    ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "cogs" / "friendly_check_errors.py",
    ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "cogs" / "friendly_errors.py",
]

def patch_file(p: Path) -> bool:
    if not p.exists():
        return False
    src = p.read_text(encoding="utf-8")
    orig = src

    if "⚠" in src and "add_reaction" in src:
        if re.search(r"\bimport\s+os\b", src) is None:
            src = re.sub(r"(?m)^(import .+|from .+ import .+)\n", r"\\g<0>import os\n", src, count=1)

        def repl(m):
            leading = m.group(1)
            call = m.group(2)
            return f"{leading}if os.getenv('REACT_WARN_ENABLE','0').lower() in ('1','true','yes'):\n{leading}{call}"

        src = re.sub(r"(?m)^(\s*)(await\s+.+?\.add_reaction\((?:['\"]⚠(?:️)?['\"]).*?\)\s*)$", repl, src)

    changed = src != orig
    if changed:
        p.write_text(src, encoding="utf-8")
    return changed

patched = 0
for f in candidates:
    if patch_file(f):
        print(f"[PATCH] {f}")
        patched += 1

if patched == 0:
    print("[INFO] Tidak ada file yang perlu dipatch atau pola tidak ditemukan.")
else:
    print(f"[OK] Patched {patched} file. Set REACT_WARN_ENABLE=1 untuk mengembalikan reaksi peringatan.")