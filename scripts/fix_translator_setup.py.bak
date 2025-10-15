#!/usr/bin/env python3
"""
fix_translator_setup.py
Minimal patcher: await add_cog di translator.setup() agar warning "coroutine was never awaited" hilang
Tidak menyentuh file konfigurasi apa pun.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

def find_translator_file() -> Path | None:
    # Lokasi standar
    candidate = Path("satpambot/bot/modules/discord_bot/cogs/translator.py")
    if candidate.exists():
        return candidate
    # Cari fallback
    for p in Path(".").rglob("translator.py"):
        # heuristik: harus berada di dalam cogs dan satpambot path
        parts = [str(x) for x in p.parts]
        if "cogs" in parts and "satpambot" in parts and p.name == "translator.py":
            return p
    return None

def main() -> int:
    target = find_translator_file()
    if target is None:
        print("ERROR: translator.py tidak ditemukan. Jalankan dari root repo.")
        return 1

    original = target.read_text(encoding="utf-8")

    # Pola 1: one-liner tanpa await
    pattern1 = re.compile(
        r"""async\s+def\s+setup\(\s*bot:\s*commands\.Bot\s*\)\s*:\s*bot\.add_cog\(\s*Translator\(bot\)\s*\)\s*(?:#.*)?""",
        re.MULTILINE,
    )

    # Pola 2: sudah benar (ada await) -> no-op
    pattern_ok = re.compile(
        r"""async\s+def\s+setup\(\s*bot:\s*commands\.Bot\s*\)\s*:\s*(?:\r?\n)+\s*await\s+bot\.add_cog\(""",
        re.MULTILINE,
    )

    if pattern_ok.search(original):
        print("OK: Tidak ada perubahan. Sudah pakai 'await bot.add_cog(...)'.")
        return 0

    if pattern1.search(original):
        patched = pattern1.sub(
            "async def setup(bot: commands.Bot):\n    await bot.add_cog(Translator(bot))  # type: ignore",
            original,
            count=1,
        )
        target.write_text(patched, encoding="utf-8")
        print(f"Patched: {target}")
        return 0

    # Pola 3: varian mirip (tanpa '# type: ignore')
    pattern2 = re.compile(
        r"""async\s+def\s+setup\(\s*bot:\s*commands\.Bot\s*\)\s*:\s*bot\.add_cog\(\s*Translator\(bot\)\s*\)""",
        re.MULTILINE,
    )
    if pattern2.search(original):
        patched = pattern2.sub(
            "async def setup(bot: commands.Bot):\n    await bot.add_cog(Translator(bot))",
            original,
            count=1,
        )
        target.write_text(patched, encoding="utf-8")
        print(f"Patched: {target}")
        return 0

    print("WARN: Pola setup() tidak ditemukan. Tidak ada perubahan yang dilakukan.")
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
