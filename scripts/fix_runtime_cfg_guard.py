#!/usr/bin/env python3



from __future__ import annotations

import re
from pathlib import Path

MARK = "THREAD/FORUM EXEMPTION — auto-inserted"



FILE = Path("satpambot/bot/modules/discord_bot/cogs/runtime_cfg_from_message.py")











def _find_func_block(src: str, name: str):



    m = re.search(rf"^([ \t]*)async\s+def\s+{name}\s*\([^)]*\):\s*\n", src, flags=re.M)



    if not m:



        return None



    base_indent = m.group(1)



    start = m.end()







    # Determine body indent from first non-empty line



    m2 = re.search(r"^(?P<i>[ \t]+)\S", src[start:], flags=re.M)



    if not m2:



        return start, start



    body_indent = m2.group("i")







    # Find end of this function by dedent



    rel = src[start:]



    pos = 0



    end = start + len(rel)



    for ln in rel.splitlines(True):



        if ln.strip() and not ln.startswith(body_indent):



            end = start + pos



            break



        pos += len(ln)



    return start, end











def _rewrite_guard_var(body: str, want: str) -> tuple[str, bool]:



    # Locate the marker line (same indent tracked)



    m = re.search(rf"^([ \t]+)# {re.escape(MARK)}\s*$", body, flags=re.M)



    if not m:



        return body, False



    ind = m.group(1)







    lines = body.splitlines(True)



    # Find start index (first line *after* marker)



    start_idx = None



    for i, ln in enumerate(lines):



        if re.match(rf"^{re.escape(ind)}# {re.escape(MARK)}\s*$", ln):



            start_idx = i + 1



            break



    if start_idx is None:



        return body, False







    # Guard block ends when we dedent (line not starting with same indent)



    end_idx = len(lines)



    for j in range(start_idx, len(lines)):



        ln = lines[j]



        if ln.strip() and not ln.startswith(ind):



            end_idx = j



            break







    changed = False



    for j in range(start_idx, end_idx):



        old = lines[j]



        lines[j] = re.sub(



            r'getattr\(\s*\w+\s*,\s*"channel"',



            f'getattr({want}, "channel"',



            lines[j],



        )



        if lines[j] != old:



            changed = True







    return "".join(lines), changed











def main() -> int:



    if not FILE.exists():



        print("[WARN] target file not found")



        return 0







    src = FILE.read_text(encoding="utf-8", errors="ignore")







    any_change = False



    for name, want in (("on_message", "message"), ("on_message_edit", "after")):



        rng = _find_func_block(src, name)



        if not rng:



            print(f"[WARN] {name} not found")



            continue



        start, end = rng



        body = src[start:end]



        new_body, changed = _rewrite_guard_var(body, want)



        if changed:



            any_change = True



            src = src[:start] + new_body + src[end:]



            print(f"[OK] updated guard var in {name} -> {want}")



        else:



            print(f"[OK] no change needed in {name}")







    if any_change:



        FILE.write_text(src, encoding="utf-8", newline="\n")



        print("[OK] file updated")



    else:



        print("[OK] nothing to update")



    return 0











if __name__ == "__main__":



    raise SystemExit(main())



