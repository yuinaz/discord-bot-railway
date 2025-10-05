#!/usr/bin/env python3



# -*- coding: utf-8 -*-



"""



Auto-fix common strict Ruff errors without changing repo config:



- E701: multiple statements on one line (colon)



- E702: multiple statements on one line (semicolon)



- EOF newline missing



Strategy:



- For lines like `if cond: stmt`, `for ...: stmt`, etc -> expand to block with proper indent.



- Split top-level semicolons into multiple lines (safe when not inside strings).



- Skip files in venv/.* cache.



Creates .bak backups next to each modified file.



Usage:



  python scripts/auto_fix_lint_v2.py /path/to/repo



"""



from __future__ import annotations

import pathlib
import re
import sys

CLAUSES = ("if","elif","else","for","while","try","except","finally","with")



CLAUSE_RE = re.compile(r"^(\s*)(" + "|".join(CLAUSES) + r")\b([^:]*):\s*(\S.*)$")







def _split_semicolons_safely(line: str) -> list[str]:



    out, cur, quote, esc = [], [], None, False



    for ch in line:



        if quote:



            cur.append(ch)



            if esc:



                esc = False



            elif ch == "\\":



                esc = True



            elif ch == quote:



                quote = None



            continue



        if ch in ("'", '"'):



            quote = ch; cur.append(ch); continue



        if ch == ";":



            out.append("".join(cur).rstrip())



            cur = []



            continue



        cur.append(ch)



    out.append("".join(cur).rstrip())



    return out







def expand_colon_oneliner(line: str):



    m = CLAUSE_RE.match(line)



    if not m:



        return None



    indent, kw, head, tail = m.groups()



    body = tail.strip()



    if not body:



        return None



    return [f"{indent}{kw}{head}:\n", f"{indent}    {body}\n"]







def process_text(text: str) -> tuple[str,bool]:



    lines = text.splitlines(True)



    changed = False



    out_lines: list[str] = []



    for raw in lines:



        ln = raw.rstrip("\n")



        if ";" in ln and not ln.lstrip().startswith("#"):



            stripped, _, cmt = ln.partition("#")



            parts = _split_semicolons_safely(stripped)



            if len(parts) > 1:



                ind = re.match(r"^(\s*)", ln).group(1)



                for p in parts:



                    if p.strip():



                        out_lines.append(f"{ind}{p.rstrip()}\n")



                if cmt:



                    out_lines.append(f"{ind}#{cmt}\n" if not cmt.startswith("#") else f"{ind}{cmt}\n")



                changed = True



                continue



        ex = expand_colon_oneliner(ln)



        if ex:



            out_lines.extend(ex); changed = True; continue



        out_lines.append(raw if raw.endswith("\n") else (raw + "\n"))



    if out_lines and not out_lines[-1].endswith("\n"):



        out_lines[-1] += "\n"; changed = True



    return "".join(out_lines), changed







def should_skip(path: pathlib.Path) -> bool:



    parts = path.parts



    return any(p.startswith((".", "__pycache__", "venv", "env", "site-packages")) for p in parts)







def main():



    base = pathlib.Path(sys.argv[1] if len(sys.argv)>1 else ".").resolve()



    changed_files = 0



    for p in base.rglob("*.py"):



        if should_skip(p):



            continue



        try:



            src = p.read_text(encoding="utf-8", errors="ignore")



        except Exception:



            continue



        new, changed = process_text(src)



        if changed:



            bak = p.with_suffix(p.suffix + ".bak")



            try: bak.write_text(src, encoding="utf-8")



            except Exception: pass



            p.write_text(new, encoding="utf-8")



            changed_files += 1



            print("[fix]", p)



    print(f"Done. Files changed: {changed_files}")



    return 0







if __name__ == "__main__":



    raise SystemExit(main())



