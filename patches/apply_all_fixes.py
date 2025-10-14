
import re, sys
from pathlib import Path

LOADER_PATHS = [
    Path("satpambot/bot/modules/discord_bot/cogs/cogs_loader.py"),
    Path("satpambot/bot/modules/discord_bot/cogs_loader.py"),
]

ENSURE = [
    "satpambot.bot.modules.discord_bot.cogs.a01_xp_checkpoint_discord_backend",
    "satpambot.bot.modules.discord_bot.cogs.a08_public_clearchat",
    "satpambot.bot.modules.discord_bot.cogs.repo_pull_and_restart",
    "satpambot.bot.modules.discord_bot.cogs.force_sync_once",
    "satpambot.bot.modules.discord_bot.cogs.github_repo_sync",
    "satpambot.bot.modules.discord_bot.cogs.weekly_xp_guard",
]

def patch_loader(p: Path):
    s = p.read_text("utf-8")
    m = re.search(r"EXTENSIONS\s*=\s*\(\s*(.*?)\)", s, flags=re.DOTALL)
    if not m:
        print(f"[fix] EXTENSIONS not found in {p}"); return
    body = m.group(1)
    entries = re.findall(r'"([^"]+)"', body)

    keep = []
    seen = set()
    for e in entries:
        if e.startswith("modules.discord_bot.cogs."):
            continue
        key = e.lower()
        if key in seen: continue
        if "selfheal" in key and any("selfheal" in x for x in keep):
            continue
        seen.add(key); keep.append(e)

    for t in ENSURE:
        if t not in keep: keep.append(t)

    new_body = "".join(f'    "{k}",\n' for k in keep)
    new_s = s[:m.start(1)] + new_body + s[m.end(1):]
    p.write_text(new_s, "utf-8")
    print(f"[fix] loader patched: {p} ({len(keep)} entries)")

def main():
    loader_done=False
    for p in LOADER_PATHS:
        if p.exists():
            patch_loader(p); loader_done=True
    if not loader_done:
        print("[fix] no loader file found")
        sys.exit(1)
    print("[fix] done. Now run: python patches/fix_add_cog_await.py")

if __name__ == "__main__":
    main()
