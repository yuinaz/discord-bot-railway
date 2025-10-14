
import re, sys
from pathlib import Path

TARGET = "satpambot.bot.modules.discord_bot.cogs.repo_pull_and_restart"

def main(path: str):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    m = re.search(r"EXTENSIONS\s*=\s*\(\s*(.*?)\)", s, flags=re.DOTALL)
    if not m:
        print("[patch] EXTENSIONS tuple not found")
        sys.exit(1)
    body = m.group(1)
    if TARGET in body:
        print("[patch] already present")
        return
    ins = f'\n    # added by patch: repo pull & restart\n    "{TARGET}",\n'
    new_s = s[:m.start(1)] + body + ins + s[m.end(1):]
    p.write_text(new_s, encoding="utf-8")
    print("[patch] injected:", TARGET)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python patches/add_repo_pull_and_restart.py <path-to-cogs_loader.py>")
        sys.exit(2)
    main(sys.argv[1])
