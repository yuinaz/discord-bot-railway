    import re, sys, os, io, pathlib

    TARGETS = [
        "satpambot/bot/modules/discord_bot/cogs/anti_image_phash_runtime.py",
        "satpambot/bot/modules/discord_bot/cogs/first_touch_attachment_ban.py",
        "satpambot/bot/modules/discord_bot/cogs/first_touch_autoban_pack_mime.py",
        "satpambot/bot/modules/discord_bot/cogs/phash_auto_ban.py",
    ]

    HEADER_SNIPPET = r'''
# --- HOTFIX: Thread/Forum exemption (no ENV needed) ---
try:
    EXEMPT_FORUM = True
except NameError:
    EXEMPT_FORUM = True

try:
    EXEMPT_CHANNELS
except NameError:
    EXEMPT_CHANNELS = {"mod-command"}

def _sb_is_thread_or_forum(ch):
    try:
        import discord
        if isinstance(ch, discord.Thread):
            return True
        parent = getattr(ch, "parent", None)
        if parent is not None and getattr(parent, "type", None) == discord.ChannelType.forum:
            return True
        # Beberapa server pakai forum channel langsung
        if getattr(ch, "type", None) == discord.ChannelType.forum:
            return True
        return False
    except Exception:
        return False
# --- END HOTFIX HEADER ---
'''.lstrip()

    GUARD_SNIPPET = r'''
        # --- HOTFIX GUARD: skip if thread/forum or exempt channel ---
        ch = getattr(message, "channel", None)
        ch_name = getattr(ch, "name", "") if ch else ""
        if _sb_is_thread_or_forum(ch) or (ch_name in EXEMPT_CHANNELS) or (EXEMPT_FORUM and getattr(ch, "is_forum", lambda: False)() if hasattr(ch, "is_forum") else False):
            try:
                self.log.debug("[hotfix] skip in thread/forum/channel='%s'", ch_name)
            except Exception:
                pass
            return
        # --- END HOTFIX GUARD ---
'''.lstrip("\n")

    def ensure_header(src: str) -> str:
        # Pasang HEADER_SNIPPET setelah import block paling atas jika belum ada
        if "_sb_is_thread_or_forum" in src:
            return src  # sudah ada
        # Cari akhir import; fallback: di paling atas file
        lines = src.splitlines(keepends=True)
        insert_idx = 0
        for i, line in enumerate(lines[:80]):  # cek 80 baris pertama cukup
            if re.match(r'^\s*(from\s+\S+\s+import|import\s+\S+)', line):
                insert_idx = i + 1
        lines.insert(insert_idx, HEADER_SNIPPET)
        return "".join(lines)

    def patch_on_message(src: str) -> str:
        # Sisipkan GUARD_SNIPPET di awal body on_message(..)
        if "[hotfix] skip in thread/forum/channel" in src:
            return src  # sudah dipatch
        # Cari definisi on_message
        m = re.search(r'^\s*async\s+def\s+on_message\s*\(\s*self\s*,\s*message\b[^)]*\)\s*:\s*$', src, flags=re.M)
        if not m:
            return src  # tidak ada on_message, biarkan
        # Tentukan indent level
        line_start = m.end()
        # Cari baris berikutnya untuk tahu indent
        post = src[line_start:]
        m2 = re.search(r'^(?P<indent>\s+)\S', post, flags=re.M)
        indent = m2.group("indent") if m2 else "    "
        guard = "".join(indent + ln if ln.strip() else ln for ln in GUARD_SNIPPET.splitlines(True))
        # Sisipkan guard setelah def line
        return src[:line_start] + guard + src[line_start:]

    def process_file(path: str):
        if not os.path.exists(path):
            print(f"[skip] {path} (not found)")
            return
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            src = f.read()
        orig = src
        src = ensure_header(src)
        src = patch_on_message(src)
        if src != orig:
            with open(path, "w", encoding="utf-8") as f:
                f.write(src)
            print(f"[ok] patched: {path}")
        else:
            print(f"[ok] already patched: {path}")

    if __name__ == "__main__":
        repo_root = pathlib.Path(__file__).resolve().parents[1]
        os.chdir(repo_root)  # cd ke root repo (patches/.. -> repo root)
        for t in TARGETS:
            process_file(t)
        print("Done.")