#!/usr/bin/env python3
import re
from pathlib import Path

COGS = Path("satpambot/bot/modules/discord_bot/cogs")
TARGETS = ["moderation_test.py","tb_alias.py","tb_shim.py","unban_fix.py","mod_ban_basic.py","ban_alias.py"]

def disable(path: Path):
    if not path.exists(): 
        print(f"[MISS] {path.name}"); return
    dst = path.with_suffix(path.suffix + ".disabled")
    if dst.exists():
        print(f"[SKIP] {dst.name} already disabled"); return
    path.rename(dst)
    print(f"[OK] {path.name} -> {dst.name}")

def patch_admin_unban():
    p = COGS / "admin.py"
    if not p.exists(): return
    txt = p.read_text(encoding="utf-8", errors="ignore")
    txt2 = re.sub(r'@commands\.command\s*\(\s*name\s*=\s*[\'"]unban[\'"]\s*\)',
                  r'# @commands.command(name="unban")  # disabled', txt, flags=re.I)
    txt2 = re.sub(r'\n\s*async def\s+unban\s*\(', r'\nasync def _disabled_unban(', txt2, flags=re.I)
    if txt2 != txt:
        p.write_text(txt2, encoding="utf-8")
        print("[OK] Disabled 'unban' in admin.py")

def main():
    for name in TARGETS:
        disable(COGS / name)
    patch_admin_unban()

if __name__ == "__main__":
    main()
