#!/usr/bin/env python3
"""
apply_patch_embed_guard.py

Safe patcher for SatpamLeina repo:
- Fix embed_scribe.upsert to guard keeper==None and optionally route to LOG_CHANNEL_ID
- Fix a03_log_autodelete_focus: await add_cog and ensure purge check is sync (no "coroutine was never awaited")

Usage:
  python apply_patch_embed_guard.py

It will create .bak backups next to each modified file and print what changed.
"""
from __future__ import annotations

import os
import re
import sys
import asyncio
from pathlib import Path
from typing import Tuple

ROOT = Path(__file__).resolve().parent

def load(p: Path) -> str:
    with p.open('r', encoding='utf-8') as f:
        return f.read()

def save_backup(p: Path) -> Path:
    bak = p.with_suffix(p.suffix + ".bak")
    if not bak.exists():
        bak.write_text(load(p), encoding='utf-8')
    return bak

def write(p: Path, s: str) -> None:
    p.write_text(s, encoding='utf-8')

def patch_embed_scribe(file_path: Path) -> Tuple[bool, str]:
    if not file_path.exists():
        return False, f"SKIP embed_scribe.py not found at {file_path}"
    src = load(file_path)
    before = src

    # 1) Ensure routing to LOG_CHANNEL_ID when route=True and bot is provided
    # Insert a helper that resolves focus channel and rebinds 'channel'
    # We'll add this once, just after the upsert signature.
    route_inject_pat = re.compile(
        r'(async\s+def\s+upsert\s*\(\s*channel\s*,\s*key\s*,\s*embed\s*,\s*\*\s*,[^)]*\):)',
        re.MULTILINE
    )
    if route_inject_pat.search(src) and "##__FOCUS_ROUTE_INJECT__" not in src:
        def repl(m):
            head = m.group(1)
            inject = """
                ##__FOCUS_ROUTE_INJECT__
                # Hard route: if route=True and LOG_CHANNEL_ID available, force send to that channel
                try:
                    _route_flag = bool(locals().get('route'))
                except Exception:
                    _route_flag = False
                _bot = locals().get('bot')
                if _route_flag and _bot is not None:
                    import os
                    _focus_raw = os.getenv('LOG_CHANNEL_ID') or os.getenv('FOCUS_LOG_CHANNEL_ID')
                    if _focus_raw:
                        try:
                            _focus_id = int(_focus_raw)
                            # Re-resolve channel from bot cache or fetch
                            ch2 = _bot.get_channel(_focus_id)
                            if ch2 is None:
                                try:
                                    ch2 = await _bot.fetch_channel(_focus_id)
                                except Exception:
                                    ch2 = None
                            if ch2 is not None:
                                channel = ch2
                        except Exception:
                            pass
            """
            return head + inject
        src = route_inject_pat.sub(repl, src, count=1)

    # 2) Replace unsafe 'ch_map[key] = int(keeper.id)' with a guarded block
    assign_pat = re.compile(r'(^\s*)ch_map\[\s*key\s*\]\s*=\s*int\(\s*keeper\.id\s*\)\s*', re.MULTILINE)
    def assign_repl(m):
        indent = m.group(1)
        block = f"""{indent}# Patched: guard keeper None -> create placeholder + optional pin
{indent}if keeper is not None:
{indent}    ch_map[key] = int(keeper.id)
{indent}else:
{indent}    _bot2 = locals().get('bot')
{indent}    if _bot2 is None:
{indent}        # Can't auto-create without bot reference; leave silently
{indent}        return False
{indent}    placeholder = await channel.send(embed=embed)
{indent}    try:
{indent}        if bool(locals().get('pin')):
{indent}            await placeholder.pin(reason="SATPAMBOT_PINNED_MEMORY (auto)")
{indent}    except Exception:
{indent}        pass
{indent}    ch_map[key] = int(placeholder.id)
{indent}    keeper = placeholder
"""
        return block
    src, n_assign = assign_pat.subn(assign_repl, src)

    changed = before != src
    if changed:
        save_backup(file_path)
        write(file_path, src)
        return True, f"OK  : embed_scribe.py patched (route_inject={ 'yes' if '##__FOCUS_ROUTE_INJECT__' in src else 'no' }, guarded_assignments={n_assign})"
    else:
        return False, "SKIP: embed_scribe.py unchanged (patterns not found or already patched)"

def patch_autodelete_focus(file_path: Path) -> Tuple[bool, str]:
    if not file_path.exists():
        return False, f"SKIP a03_log_autodelete_focus.py not found at {file_path}"
    src = load(file_path)
    before = src

    # 1) Await add_cog inside async setup
    # Replace "bot.add_cog(" with "await bot.add_cog(" only within setup(...)
    setup_block_pat = re.compile(r'(async\s+def\s+setup\s*\(\s*bot\s*\)\s*:\s*)([\s\S]*?)(?=^\S|\Z)', re.MULTILINE)
    def setup_repl(m):
        header, body = m.group(1), m.group(2)
        body_new = body.replace("bot.add_cog(", "await bot.add_cog(")
        return header + body_new
    src = setup_block_pat.sub(setup_repl, src)

    # 2) Make purge check sync (avoid "coroutine was never awaited" on local _check)
    src = re.sub(r'async\s+def\s+_check\s*\(', 'def _check(', src)

    changed = before != src
    if changed:
        save_backup(file_path)
        write(file_path, src)
        return True, "OK  : a03_log_autodelete_focus.py patched (await add_cog + sync check)"
    else:
        return False, "SKIP: a03_log_autodelete_focus.py unchanged (already patched or pattern not found)"

def main() -> int:
    # Resolve files
    embed_path = ROOT / "satpambot" / "bot" / "utils" / "embed_scribe.py"
    auto_focus_path = ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "cogs" / "a03_log_autodelete_focus.py"

    results = []

    ok, msg = patch_embed_scribe(embed_path)
    results.append(msg)

    ok2, msg2 = patch_autodelete_focus(auto_focus_path)
    results.append(msg2)

    print("\n".join(results))
    # Friendly reminders
    print("NOTE: ensure your env has LOG_CHANNEL_ID set (e.g., 1400375184048787566).")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())



from discord.ext import commands
async def setup(bot: commands.Bot):
    # auto-register Cog classes defined in this module
    for _name, _obj in globals().items():
        try:
            if isinstance(_obj, type) and issubclass(_obj, commands.Cog):
                await bot.add_cog(_obj(bot))
        except Exception:
            continue
