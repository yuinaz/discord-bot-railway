from pathlib import Path

TARGETS = [
    "a01_xp_checkpoint_discord_backend",
    "a08_public_clearchat",
    "public_chat_gate",
    "public_send_router",
    "repo_guild_sync_bootstrap",
    "a02_miner_accel_overlay",
    "a06_sticky_status_strict_overlay",
    "vision_captioner",
    "qna_dual_provider",
    "admin_sync",
]

def main():
    p = Path("satpambot/bot/modules/discord_bot/cogs/cogs_loader.py")
    if not p.exists():
        p = Path("satpambot/bot/modules/discord_bot/cogs_loader.py")
    s = p.read_text("utf-8", errors="ignore")
    missing = [t for t in TARGETS if t not in s]
    present = [t for t in TARGETS if t in s]
    print("Present:", present)
    print("Missing:", missing)
    if missing:
        print("\nRun:  python patches/enable_cogs_patch.py", p.as_posix())

if __name__ == "__main__":
    main()
