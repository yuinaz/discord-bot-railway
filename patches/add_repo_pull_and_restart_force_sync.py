
import re, sys
from pathlib import Path
TARGETS = [
    "satpambot.bot.modules.discord_bot.cogs.repo_pull_and_restart",
    "satpambot.bot.modules.discord_bot.cogs.force_sync_once",
]

def main(path: str):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    m = re.search(r"EXTENSIONS\s*=\s*\(\s*(.*?)\)", s, flags=re.DOTALL)
    if not m:
        print("[patch] EXTENSIONS tuple not found")
        sys.exit(1)
    body = m.group(1)
    inserted = False
    for tgt in TARGETS:
        if tgt not in body:
            body += f'\n    "{tgt}",'
            inserted = True
    if not inserted:
        print("[patch] already present")
        return
    new_s = s[:m.start(1)] + body + s[m.end(1):]
    p.write_text(new_s, encoding="utf-8")
    print("[patch] injected:", ", ".join(TARGETS))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python patches/add_repo_pull_and_restart_force_sync.py <path-to-cogs_loader.py>")
        sys.exit(2)
    main(sys.argv[1])
