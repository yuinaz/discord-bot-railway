
import re, sys
from pathlib import Path

TARGET = "satpambot.bot.modules.discord_bot.cogs.force_sync_autoheal"
REMOVE = "satpambot.bot.modules.discord_bot.cogs.force_sync_once"

def patch(path: str):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    m = re.search(r"EXTENSIONS\s*=\s*\(\s*(.*?)\)", s, flags=re.DOTALL)
    if not m:
        print("[patch] EXTENSIONS tuple not found"); sys.exit(1)
    body = m.group(1)
    entries = re.findall(r'"([^"]+)"', body)
    new = []
    seen = set()
    for e in entries:
        if e == REMOVE: 
            continue
        if e in seen: 
            continue
        seen.add(e); new.append(e)
    if TARGET not in new:
        new.append(TARGET)
    new_body = "".join(f'    "{k}",\n' for k in new)
    out = s[:m.start(1)] + new_body + s[m.end(1):]
    p.write_text(out, encoding="utf-8")
    print("[patch] applied; added autoheal, removed old force_sync_once")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python patches/add_force_sync_autoheal.py <path-to-cogs_loader.py>"); sys.exit(2)
    patch(sys.argv[1])
