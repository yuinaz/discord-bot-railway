#!/usr/bin/env python3
"""
scripts/disable_ban_modules.py
- Renames ban-related cogs so they won't be loaded
- Targets:
    satpambot/.../cogs/mod_ban_basic.py  -> mod_ban_basic.py.disabled
    satpambot/.../cogs/ban_alias.py      -> ban_alias.py.disabled
    satpambot/.../cogs/admin.py          -> (comment out 'unban' OR rename file if you prefer)
"""
import os, sys, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # repo root
COGS = ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "cogs"

targets = [
    "mod_ban_basic.py",
    "ban_alias.py",
]

def rename(p: Path):
    if p.exists() and p.is_file():
        dst = p.with_suffix(p.suffix + ".disabled")
        if not dst.exists():
            p.rename(dst)
            print(f"[OK] Renamed {p.name} -> {dst.name}")
        else:
            print(f"[SKIP] Already disabled: {dst.name}")
    else:
        print(f"[MISS] {p.name} not found")

def comment_unban(admin_path: Path):
    if not admin_path.exists():
        print("[MISS] admin.py not found")
        return
    txt = admin_path.read_text(encoding="utf-8", errors="ignore")
    # Disable the unban command by renaming function and decorator
    txt2 = re.sub(r'@commands\.command\s*\(\s*name\s*=\s*[\'"]unban[\'"]\s*\)',
                  r'# @commands.command(name="unban")  # disabled by script', txt, flags=re.I)
    txt2 = re.sub(r'\n\s*async def\s+unban\s*\(', r'\nasync def _disabled_unban(', txt2, flags=re.I)
    if txt2 != txt:
        admin_path.write_text(txt2, encoding="utf-8")
        print("[OK] Disabled 'unban' in admin.py")
    else:
        print("[SKIP] Could not find 'unban' pattern in admin.py (maybe already disabled?)")

def main():
    for name in targets:
        rename(COGS / name)
    comment_unban(COGS / "admin.py")

if __name__ == "__main__":
    main()
