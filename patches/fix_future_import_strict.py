#!/usr/bin/env python3







"""







Fixes: SyntaxError: from __future__ imports must occur at the beginning of the file







Target: satpambot/bot/modules/discord_bot/cogs/anti_image_phash_runtime_strict.py







- Move `from __future__ import annotations` to the very top (after shebang/encoding + optional module docstring)







- Deduplicate if it appears multiple times







Safe to run multiple times (idempotent).







"""















import re
from pathlib import Path

TARGET = Path("satpambot/bot/modules/discord_bot/cogs/anti_image_phash_runtime_strict.py")























def find_docstring_end(lines, start_idx):







    # If first meaningful line is a triple-quoted string, treat it as module docstring







    if start_idx >= len(lines):







        return start_idx







    m = re.match(r'^\s*(?:[rubf]{0,3})?([\'"]{3})', lines[start_idx], re.I)







    if not m:







        return start_idx







    quote = m.group(1)







    # If docstring closes on same line







    if lines[start_idx].count(quote) >= 2:







        return start_idx + 1







    # else search forward







    i = start_idx + 1







    while i < len(lines):







        if quote in lines[i]:







            return i + 1







        i += 1







    # Unterminated, fail open







    return start_idx + 1























def main():







    if not TARGET.exists():







        print(f"[ERROR] File not found: {TARGET}")







        raise SystemExit(2)







    txt = TARGET.read_text(encoding="utf-8")







    lines = txt.splitlines(True)















    i = 0







    # Shebang







    if i < len(lines) and lines[i].startswith("#!"):







        i += 1







    # Encoding and blank lines







    while i < len(lines) and (re.match(r"^\s*#.*coding[:=]\s*[-\w.]+", lines[i]) or lines[i].strip() == ""):







        i += 1















    # Optional module docstring







    insert_at = find_docstring_end(lines, i)















    # Remove all future-annotation imports anywhere







    future_re = re.compile(r"^\s*from\s+__future__\s+import\s+annotations\s*$", re.I)







    removed = False







    k = 0







    new_lines = []







    for ln in lines:







        if future_re.match(ln):







            removed = True







            continue







        new_lines.append(ln)







    lines = new_lines















    # Recompute insert_at if earlier lines count changed (we only removed future lines above the insert point in rare cases)







    # We can simply re-scan since it's cheap.







    i = 0







    if i < len(lines) and lines[i].startswith("#!"):







        i += 1







    while i < len(lines) and (re.match(r"^\s*#.*coding[:=]\s*[-\w.]+", lines[i]) or lines[i].strip() == ""):







        i += 1







    insert_at = find_docstring_end(lines, i)















    # Insert canonical future line







    future_line = "from __future__ import annotations\n"







    # Only insert if not already present at the correct place (very unlikely after removal)







    # But we unconditionally insert for determinism.







    lines[insert_at:insert_at] = [future_line]







    if insert_at + 1 < len(lines) and lines[insert_at + 1].strip() != "":







        lines.insert(insert_at + 1, "\n")















    new_txt = "".join(lines)







    if new_txt != txt:







        TARGET.write_text(new_txt, encoding="utf-8", newline="\n")







        print(f"[OK] Reordered future import to top: {TARGET}")







    else:







        print("[OK] No change needed (already correct).")























if __name__ == "__main__":







    main()







