#!/usr/bin/env python3
import os, re, sys, shutil
from pathlib import Path

ROOT = Path.cwd()

targets = [
    ("satpambot/bot/modules/discord_bot/cogs/a20_curriculum_tk_sd.py", "curriculum"),
    ("satpambot/bot/modules/discord_bot/cogs/a23_auto_graduate_overlay.py", "grad"),
    ("satpambot/bot/modules/discord_bot/cogs/presence_from_file.py", "presence"),
    ("satpambot/bot/utils/xp_state_discord.py", "xpstate"),
]

def backup(path: Path):
    bak = path.with_suffix(path.suffix + ".bak")
    if not bak.exists():
        shutil.copy2(path, bak)
    return bak

def patch_curriculum(p: Path):
    s = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    out = []
    injected = 0
    for i, line in enumerate(s):
        if re.search(r'obj\s*\[\s*["\']xp_total["\']\s*\]\s*=\s*max\(', line):
            out.append("obj = {} if not isinstance(obj, dict) else obj")
            injected += 1
        out.append(line)
    if injected:
        backup(p)
        p.write_text("\n".join(out), encoding="utf-8")
    return injected

def replace_var_gets(text: str, vars_):
    for v in vars_:
        text = re.sub(rf'(?<!\()(?<!\w)({v})\.get\(', r'(\\1 or {}).get(', text)
    return text

def patch_simple_gets(p: Path, vars_):
    s = p.read_text(encoding="utf-8", errors="ignore")
    t = replace_var_gets(s, vars_)
    if t != s:
        backup(p)
        p.write_text(t, encoding="utf-8")
        return True
    return False

def main():
    any_change = 0
    for rel, kind in targets:
        path = ROOT / rel
        if not path.exists():
            print(f"[MISS] {rel}")
            continue
        if kind == "curriculum":
            n = patch_curriculum(path)
            print(f"[OK] curriculum guard injected: {n} place(s)")
            any_change += n
        elif kind == "grad":
            ok = patch_simple_gets(path, ["data","obj","state","conf","cfg","info"])
            print(f"[OK] grad guard:", "changed" if ok else "no-change")
            any_change += int(ok)
        elif kind == "presence":
            ok = patch_simple_gets(path, ["data","obj","conf","cfg","state"])
            print(f"[OK] presence guard:", "changed" if ok else "no-change")
            any_change += int(ok)
        elif kind == "xpstate":
            ok = patch_simple_gets(path, ["data"])
            print(f"[OK] xp_state guard:", "changed" if ok else "no-change")
            any_change += int(ok)
    if not any_change:
        print("No changes applied (files already guarded or patterns not found).")

if __name__ == "__main__":
    main()
