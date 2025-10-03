#!/usr/bin/env python3
import re
from pathlib import Path

TARGET = Path('satpambot/bot/modules/discord_bot/cogs/runtime_cfg_from_message.py')

def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')

def write(path: Path, s: str) -> None:
    path.write_text(s, encoding='utf-8', newline='\n')

def cleanup_noise(s: str) -> str:
    # Remove standalone 'low' lines or obvious duplicates from accidental merges
    lines = s.splitlines(True)
    out = []
    for ln in lines:
        if ln.strip() == "low":
            continue
        out.append(ln)
    return "".join(out)

def fix_guard_for_func(s: str, func_name: str, want_var: str) -> tuple[str, bool]:
    \"\"\"
    Find function 'func_name', then find the first guard marker line in its body.
    Within the next ~100 lines at the same indent (guard window), rewrite any
    getattr(<ident>, "channel", ...) to getattr(want_var, "channel", ...)
    \"\"\"
    changed = False
    # iterate over all functions named func_name (safety)
    func_pat = re.compile(rf'^([ \t]*)async\s+def\s+{func_name}\s*\([^)]*\):\s*\r?\n', re.M)
    pos = 0
    while True:
        m = func_pat.search(s, pos)
        if not m:
            break
        base_indent = m.group(1)
        fn_start = m.end()
        # function end: until next def/class at same or less indent
        tail = s[fn_start:]
        end_pat = re.compile(rf'^(?:{base_indent}@|\s*async\s+def|\s*class)\b', re.M)
        m_end = end_pat.search(tail)
        fn_end = fn_start + (m_end.start() if m_end else len(s) - fn_start)
        body = s[fn_start:fn_end]

        # find guard marker
        mark_pat = re.compile(r'^([ \t]+)# THREAD/FORUM EXEMPTION — auto-inserted\s*$', re.M)
        mm = mark_pat.search(body)
        if not mm:
            pos = fn_end
            continue  # nothing to fix in this func

        indent = mm.group(1)
        after = body[mm.end():]
        # Build guard window (max 100 lines, stop when dedent out of indent)
        lines = after.splitlines(True)
        win_len = 0
        kept = []
        for ln in lines:
            if ln.strip() and not ln.startswith(indent):
                break
            kept.append(ln)
            win_len += len(ln)
            if len(kept) >= 100:
                break
        win = "".join(kept)
        # Rewrite any getattr(<ident>, "channel" ...) to want_var
        new_win = re.sub(
            r'getattr\(\s*[A-Za-z_][A-Za-z0-9_]*\s*,\s*\"channel\"',
            f'getattr({want_var}, "channel"',
            win
        )
        if new_win != win:
            changed = True
            # stitch back
            new_body = body[:mm.end()] + new_win + body[mm.end()+len(win):]
            s = s[:fn_start] + new_body + s[fn_end:]
            # update slicing positions based on delta
            delta = len(new_body) - len(body)
            fn_end += delta

        pos = fn_end

    return s, changed

def main():
    s = read(TARGET)
    orig = s
    s = cleanup_noise(s)
    s, a = fix_guard_for_func(s, 'on_message', 'message')
    s, b = fix_guard_for_func(s, 'on_message_edit', 'after')

    if s != orig:
        write(TARGET, s)
        print(f"Updated {TARGET} (on_message fixed={a}, on_message_edit fixed={b})")
    else:
        print("No changes needed.")

if __name__ == "__main__":
    main()
