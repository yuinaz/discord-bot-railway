#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
retrofit_patcher.py
- Tambah helper retrofit() ke smoke_utils (helper & scripts) agar instance DummyBot yang "kurus" punya API minimal.
- Perbaiki import & pemanggilan retrofit() di scripts/smoke_deep.py tanpa merusak config/format.
Safe idempotent: bisa dijalankan berkali-kali, selalu buat file .bak-<epoch> sebelum ubah.
"""

import os, re, sys, time
from pathlib import Path

ROOT = Path(os.getcwd())

RETROFIT_FUN = r"""
# --- retrofit helpers (safe no-op shims) ---
def retrofit(bot):
    \"\"\"Ensure a skinny bot instance has the APIs our cogs expect.\"\"\"
    import types

    async def _noop(self, *a, **kw):
        return None

    # wait_until_ready() dipakai banyak loop
    if not hasattr(bot, "wait_until_ready"):
        bot.wait_until_ready = types.MethodType(_noop, bot)

    # channel & user helpers dipakai beberapa cog
    if not hasattr(bot, "get_all_channels"):
        bot.get_all_channels = types.MethodType(lambda self: [], bot)

    if not hasattr(bot, "get_channel"):
        bot.get_channel = types.MethodType(lambda self, _id: None, bot)

    if not hasattr(bot, "get_user"):
        bot.get_user = types.MethodType(lambda self, _id: None, bot)

    if not hasattr(bot, "fetch_user"):
        async def _fetch_user(self, _id):
            return None
        bot.fetch_user = types.MethodType(_fetch_user, bot)

    # optional: add_check supaya gate check gak error
    if not hasattr(bot, "add_check"):
        bot.add_check = types.MethodType(lambda self, f: None, bot)

    return bot
""".strip("\n") + "\n"

def _backup(path: Path):
    bak = path.with_suffix(path.suffix + f".bak-{int(time.time())}")
    bak.write_bytes(path.read_bytes())
    print(f"[bak] {bak}")
    return bak

def patch_smoke_utils(path: Path):
    print(f"[scan] {path}")
    src = path.read_text(encoding="utf-8")
    if "def retrofit(bot):" in src:
        print("[ok ] retrofit() sudah ada — skip")
        return False
    # sisipkan di akhir file
    _backup(path)
    # pastikan ada satu newline sebelum tambah
    new_src = src.rstrip("\n") + "\n\n" + RETROFIT_FUN
    path.write_text(new_src, encoding="utf-8")
    print(f"[ok ] retrofit() ditambahkan ke {path}")
    return True

def patch_import_block(deep_path: Path):
    print(f"[scan] {deep_path}")
    src = deep_path.read_text(encoding="utf-8")
    changed = False

    # 1) pastikan import prefer helper dulu
    IMPORT_BLOCK = (
        "try:\n"
        "    from satpambot.bot.modules.discord_bot.helpers import smoke_utils as smoke_utils\n"
        "except Exception:\n"
        "    import smoke_utils\n"
    )

    if "helpers import smoke_utils as smoke_utils" in src:
        # sudah ada
        pass
    elif re.search(r"(?m)^\s*import\s+smoke_utils\s*$", src) or \
         re.search(r"(?m)^\s*from\s+scripts\s+import\s+smoke_utils\s*$", src):
        # ganti import single menjadi block
        _backup(deep_path); changed = True
        src = re.sub(r"(?m)^\s*import\s+smoke_utils\s*$", IMPORT_BLOCK, src)
        src = re.sub(r"(?m)^\s*from\s+scripts\s+import\s+smoke_utils\s*$", IMPORT_BLOCK, src)
    elif "import smoke_utils" not in src:
        # tidak ada sama sekali; sisipkan setelah shebang/encoding/initial imports
        _backup(deep_path); changed = True
        # taruh di paling atas setelah future/import blok pertama
        m = re.search(r"(?s)\A(.*?\n)(?=[^\n]*import|\Z)", src)
        insert_at = 0
        if m:
            insert_at = len(m.group(1))
        src = src[:insert_at] + IMPORT_BLOCK + "\n" + src[insert_at:]
    # 2) tambahkan pemanggilan retrofit setelah instansiasi DummyBot
    def _inject_retrofit(match):
        var = match.group(1)
        tail = match.group(0)
        if re.search(rf"smoke_utils\.retrofit\(\s*{re.escape(var)}\s*\)", tail):
            return tail
        return tail + f"\nsmoke_utils.retrofit({var})  # ensure shims for smoke\n"

    pattern = re.compile(r"(?m)^(\w+)\s*=\s*(?:smoke_utils\.)?(?:_?DummyBot)\s*\([^)]*\)\s*$")
    if pattern.search(src):
        if not re.search(r"smoke_utils\.retrofit\(", src):
            src = pattern.sub(_inject_retrofit, src, count=1)
            changed = True
            print("[ok ] retrofit() dipanggil setelah pembuatan DummyBot")
    else:
        print("[warn] Tidak menemukan baris pembuatan DummyBot di smoke_deep.py — tambahkan manual jika perlu.")

    if changed:
        deep_path.write_text(src, encoding="utf-8")
        print(f"[ok ] import/call retrofit diperbarui: {deep_path}")
    else:
        print("[ok ] import & retrofit call sudah sesuai — no change")
    return changed

def main():
    # target files
    helper_smoke = ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "helpers" / "smoke_utils.py"
    scripts_smoke = ROOT / "scripts" / "smoke_utils.py"  # optional
    smoke_deep = ROOT / "scripts" / "smoke_deep.py"

    any_change = False
    if helper_smoke.exists():
        any_change |= patch_smoke_utils(helper_smoke)
    else:
        print(f"[skip] {helper_smoke} tidak ditemukan")

    if scripts_smoke.exists():
        any_change |= patch_smoke_utils(scripts_smoke)
    else:
        print(f"[info] {scripts_smoke} optional; tidak ada")

    if smoke_deep.exists():
        any_change |= patch_import_block(smoke_deep)
    else:
        print(f"[skip] {smoke_deep} tidak ditemukan")

    if not any_change:
        print("[done] Tidak ada perubahan. Semua sudah patched.")
    else:
        print("[done] Patch selesai. Jalankan kembali smoke_deep.py")

if __name__ == "__main__":
    main()
