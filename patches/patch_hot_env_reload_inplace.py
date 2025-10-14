
#!/usr/bin/env python3
# Patch hot_env_reload.py to safely reload async/sync across discord.py variants.
# - Inserts helper import:
#     from satpambot.bot.modules.discord_bot.helpers.hotenv_reload_helpers import reload_extensions_safely
# - Replaces a simple for-loop that calls self.bot.reload_extension(ext) with a call to reload_extensions_safely(...)
#
# Backups the original file as hot_env_reload.py.bak-<epoch>.
#
# Run from repo root:
#   python patches/patch_hot_env_reload_inplace.py
# Or specify a custom path:
#   python patches/patch_hot_env_reload_inplace.py path/to/hot_env_reload.py

import re, sys, os, time, io

def find_hotenv_file(start_dir):
    candidates = [
        "satpambot/bot/modules/discord_bot/cogs/hot_env_reload.py",
        "bot/modules/discord_bot/cogs/hot_env_reload.py",
        "hot_env_reload.py",
    ]
    for c in candidates:
        p = os.path.join(start_dir, c)
        if os.path.isfile(p):
            return p
    # Deep search (last resort)
    for dirpath, _, filenames in os.walk(start_dir):
        for fn in filenames:
            if fn == "hot_env_reload.py" and "cogs" in dirpath.replace("\\", "/"):
                return os.path.join(dirpath, fn)
    return None

def ensure_import(text):
    imp = "from satpambot.bot.modules.discord_bot.helpers.hotenv_reload_helpers import reload_extensions_safely"
    if imp in text:
        return text, False
    # Insert after last import block near the top
    lines = text.splitlines()
    insert_idx = 0
    for i, line in enumerate(lines[:200]):
        if line.strip().startswith("import") or line.strip().startswith("from "):
            insert_idx = i + 1
    lines.insert(insert_idx, imp)
    new_text = "\n".join(lines)
    if not new_text.endswith("\n"):
        new_text += "\n"
    return new_text, True

def replace_for_loop(text):
    """
    Replace patterns like:
        for X in EXTS:
            self.bot.reload_extension(...)
    with:
        reload_extensions_safely(self.bot, EXTS, logger=globals().get('log'), skip_self=__name__)
    """
    pattern = re.compile(
        r"for\s+(?P<var>\w+)\s+in\s+(?P<src>[^\:\n]+):\s*\n(?P<body>(?:[ \t]+.+\n)+)",
        re.DOTALL,
    )

    count = 0
    pos = 0
    out = io.StringIO()
    for m in pattern.finditer(text):
        body = m.group("body")
        if "self.bot.reload_extension(" not in body:
            continue
        src = m.group("src").strip()
        replacement = f"reload_extensions_safely(self.bot, {src}, logger=globals().get('log'), skip_self=__name__)\n"
        out.write(text[pos:m.start()])
        out.write(replacement)
        pos = m.end()
        count += 1

    out.write(text[pos:])
    return out.getvalue(), count

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else find_hotenv_file(os.getcwd())
    if not target or not os.path.isfile(target):
        print("[patcher] ERROR: hot_env_reload.py not found. Provide path explicitly.", file=sys.stderr)
        sys.exit(2)

    print(f"[patcher] Target: {target}")
    with open(target, "r", encoding="utf-8") as f:
        original = f.read()

    text, imported = ensure_import(original)
    text2, replaced = replace_for_loop(text)

    if not imported and replaced == 0 and "reload_extensions_safely(" in original:
        print("[patcher] Nothing to patch: helper already used.")
        sys.exit(0)

    bak = f"{target}.bak-{int(time.time())}"
    with open(bak, "w", encoding="utf-8") as f:
        f.write(original)
    print(f"[patcher] Backup written to: {bak}")

    with open(target, "w", encoding="utf-8") as f:
        f.write(text2)
    print(f"[patcher] Done. import_added={imported} loops_replaced={replaced}")

    print("\n[Next] Recommended checks:")
    print("  - set PYTHONWARNINGS=error  (Windows) or export PYTHONWARNINGS=error (Linux/macOS)")
    print("  - Trigger a change to SatpamBot.env and watch logs for any 'was never awaited' warnings.")
    print("  - Run your smoke tests: python -m scripts.smoke_cogs.py")

if __name__ == "__main__":
    main()
