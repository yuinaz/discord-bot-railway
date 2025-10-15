#!/usr/bin/env python3
"""
apply_minifix_2025_09_03.py
- Menambah *compat shim* minimal tanpa mengubah config/env:
  1) helpers/__init__.py -> expose stdlib `re` & `json` sebagai atribut modul helpers
  2) helpers/errorlog_helper.py -> tambahkan fungsi `log_error_embed(...)` jika belum ada
Pemakaian:
  python scripts/apply_minifix_2025_09_03.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
helpers_dir = ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "helpers"
init_file = helpers_dir / "__init__.py"
err_file  = helpers_dir / "errorlog_helper.py"

def ensure_helpers_init_exports():
    code = """
# --- compat: expose stdlib re/json for legacy imports ---
try:
    import re as _compat_re, json as _compat_json  # noqa: F401
    re = _compat_re
    json = _compat_json
except Exception:
    pass
"""
    txt = init_file.read_text(encoding="utf-8")
    if "compat: expose stdlib re/json" in txt:
        return False, "helpers.__init__: compat already present"
    init_file.write_text(txt.rstrip() + "\n" + code, encoding="utf-8")
    return True, "helpers.__init__: compat appended"

def ensure_errorlog_helper_embed():
    code = """
# --- compat: add log_error_embed if missing ---
try:
    log_error_embed
except NameError:
    import discord  # type: ignore
    async def log_error_embed(channel, title: str, description: str):
        try:
            emb = discord.Embed(title=title, description=description, color=0xE74C3C)
            await channel.send(embed=emb)
        except Exception:
            # Fallback teks supaya tidak memutus alur
            try:
                await channel.send(f"[ERROR] {title}: {description}")
            except Exception:
                pass
"""
    txt = err_file.read_text(encoding="utf-8")
    if "compat: add log_error_embed" in txt or "def log_error_embed" in txt:
        return False, "errorlog_helper: function already present"
    err_file.write_text(txt.rstrip() + "\n" + code, encoding="utf-8")
    return True, "errorlog_helper: function appended"

def main():
    changed = []
    for p in (init_file, err_file):
        if not p.exists():
            print(f"[ERR] Missing file: {p}")
            sys.exit(1)
    a, msg1 = ensure_helpers_init_exports(); print(msg1)
    b, msg2 = ensure_errorlog_helper_embed(); print(msg2)
    if a or b:
        print("[OK] Compat minifix applied.")
        sys.exit(0)
    else:
        print("[OK] Nothing to change (already applied).")
        sys.exit(0)

if __name__ == "__main__":
    main()
