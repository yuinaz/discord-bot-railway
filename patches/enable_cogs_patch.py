import re, sys
from pathlib import Path

TARGETS = [
    "satpambot.bot.modules.discord_bot.cogs.a01_xp_checkpoint_discord_backend",
    "satpambot.bot.modules.discord_bot.cogs.a08_public_clearchat",
    "satpambot.bot.modules.discord_bot.cogs.public_chat_gate",
    "satpambot.bot.modules.discord_bot.cogs.public_send_router",
    "satpambot.bot.modules.discord_bot.cogs.repo_guild_sync_bootstrap",
    "satpambot.bot.modules.discord_bot.cogs.a02_miner_accel_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a06_sticky_status_strict_overlay",
    "satpambot.bot.modules.discord_bot.cogs.vision_captioner",
    "satpambot.bot.modules.discord_bot.cogs.qna_dual_provider",
    "satpambot.bot.modules.discord_bot.cogs.admin_sync",
]

def main(path: str):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    m = re.search(r"EXTENSIONS\s*=\s*\(\s*(.*?)\)", s, flags=re.DOTALL)
    if not m:
        print("[patch] EXTENSIONS tuple not found in", path)
        sys.exit(1)
    body = m.group(1)
    missing = [t for t in TARGETS if t not in body]
    if not missing:
        print("[patch] nothing to add")
        return
    ins = "\n    # --- added by patch: enable missing cogs ---\n" + "".join(f'    "{t}",\n' for t in missing)
    new_body = body + ins
    new_s = s[:m.start(1)] + new_body + s[m.end(1):]
    p.write_text(new_s, encoding="utf-8")
    print(f"[patch] added {len(missing)} entries:", ", ".join(missing))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python patches/enable_cogs_patch.py <path-to-cogs_loader.py>")
        sys.exit(2)
    main(sys.argv[1])
