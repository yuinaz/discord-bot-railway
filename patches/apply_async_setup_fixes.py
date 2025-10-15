import re, time, os, sys, io, pathlib

TARGETS = [
    "satpambot/bot/modules/discord_bot/cogs/a06_status_coalescer_wildcard_overlay.py",
    "satpambot/bot/modules/discord_bot/cogs/learning_passive_observer.py",
    "satpambot/bot/modules/discord_bot/cogs/learning_passive_observer_persist.py",
    "satpambot/bot/modules/discord_bot/cogs/phish_log_sticky_example.py",
    "satpambot/bot/modules/discord_bot/cogs/phish_log_sticky_guard.py",
    "satpambot/bot/modules/discord_bot/cogs/qna_dual_provider.py",
]

IMPORT_LINE = "from satpambot.bot.modules.discord_bot.helpers.cog_utils import safe_add_cog\n"

def patch_file(path: str):
    if not os.path.exists(path):
        print(f"[skip] not found: {path}")
        return False

    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    orig = src

    # Inject import if missing
    if "safe_add_cog" not in src:
        # Put after the first import line if possible
        m = re.search(r"^(from\s+.+\s+import\s+.+|import\s+.+)$", src, flags=re.M|re.I)
        if m:
            idx = m.end()
            src = src[:idx] + "\n" + IMPORT_LINE + src[idx:]
        else:
            src = IMPORT_LINE + src

    # def setup(bot): -> async def setup(bot):
    src = re.sub(r"\bdef\s+setup\s*\(\s*bot\s*\):", "async def setup(bot):", src)

    # bot.add_cog( ... ) -> await safe_add_cog(bot, ... )
    # Do not double-convert if already awaited
    src = re.sub(r"(?<!await\s)bot\.add_cog\s*\(", "await safe_add_cog(bot, ", src)

    if src != orig:
        # backup
        bak = f"{path}.bak-{int(time.time())}"
        with open(bak, "w", encoding="utf-8") as f:
            f.write(orig)
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        print(f"[ok ] patched: {path} (backup: {os.path.basename(bak)})")
        return True
    else:
        print(f"[skip] already patched: {path}")
        return False

def main():
    base = pathlib.Path.cwd()
    any_patched = False
    for rel in TARGETS:
        p = base / rel
        any_patched |= bool(patch_file(str(p)))
    if any_patched:
        print("[done] Some files were patched. Rebuild/restart your bot.")
    else:
        print("[done] Nothing to patch.")

if __name__ == "__main__":
    main()
