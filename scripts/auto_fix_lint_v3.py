#!/usr/bin/env python3
from __future__ import annotations



# -*- coding: utf-8 -*-



"""



Auto-fix lint (v3) for large repos — without changing ruff config.



Fixes:



- E701: multiple statements after ':' (if/elif/else/for/while/try/except/finally/with)



- E704: one-line function definition (def ...: stmt)  -> expand



- Class one-liners: class X(...): stmt -> expand



- E702/E703: split semicolons into separate statements (outside strings)



- W291/W293: strip trailing whitespace; normalize blank lines



- Ensure newline at EOF



Creates .bak backups next to each modified file.



Usage:



  python scripts/auto_fix_lint_v3.py /path/to/repo



"""




import pathlib
import re
import sys

CLAUSES = ("if","elif","else","for","while","try","except","finally","with")



RE_COLON_CLAUSE = re.compile(r"^(\s*)(" + "|".join(CLAUSES) + r")\b([^:]*):\s*(\S.*)$")



RE_DEF_ONELINER = re.compile(r"^(\s*)(def\s+\w+\s*\([^)]*\))\s*:\s*(\S.*)$")



RE_CLASS_ONELINER = re.compile(r"^(\s*)(class\s+\w+\s*(\([^)]*\))?)\s*:\s*(\S.*)$")







def _split_semicolons_safely(line: str) -> list[str]:



    out, cur, quote, esc = [], [], None, False



    i = 0



    while i < len(line):



        ch = line[i]



        if quote:



            cur.append(ch)



            if esc:



                esc = False



            elif ch == "\\":



                esc = True



            elif ch == quote:



                quote = None



            i += 1; continue



        if ch in ("'", '"'):



            quote = ch; cur.append(ch); i += 1; continue



        if ch == ";":



            out.append("".join(cur).rstrip())



            cur = []



            i += 1; continue



        cur.append(ch); i += 1



    out.append("".join(cur).rstrip())



    return out







def _expand_clause_oneliner(line: str):



    m = RE_COLON_CLAUSE.match(line)



    if not m: return None



    indent, kw, head, tail = m.groups()



    stmt = tail.strip()



    if not stmt: return None



    return [f"{indent}{kw}{head}:\n", f"{indent}    {stmt}\n"]







def _expand_def_oneliner(line: str):



    m = RE_DEF_ONELINER.match(line)



    if not m: return None



    indent, signature, tail = m.groups()



    parts = _split_semicolons_safely(tail)



    out = [f"{indent}{signature}:\n"]



    wrote = False



    for p in parts:



        if p.strip():



            out.append(f"{indent}    {p.strip()}\n")



            wrote = True



    if not wrote:



        out.append(f"{indent}    pass\n")



    return out







def _expand_class_oneliner(line: str):



    m = RE_CLASS_ONELINER.match(line)



    if not m: return None



    indent, header, _paren, tail = m.groups()



    parts = _split_semicolons_safely(tail)



    out = [f"{indent}{header}:\n"]



    wrote = False



    for p in parts:



        if p.strip():



            out.append(f"{indent}    {p.strip()}\n")



            wrote = True



    if not wrote:



        out.append(f"{indent}    pass\n")



    return out







def process_text(text: str) -> tuple[str,bool]:



    changed = False



    lines_in = text.splitlines(True)



    lines_out = []



    for raw in lines_in:



        has_nl = raw.endswith(("\\r\\n","\\n"))



        body = raw[:-1] if has_nl else raw



        body = body.rstrip(" \\t")



        ln = body







        if ";" in ln and not ln.lstrip().startswith("#"):



            stripped, _, cmt = ln.partition("#")



            parts = _split_semicolons_safely(stripped)



            if len(parts) > 1:



                ind = re.match(r"^(\\s*)", ln).group(1)



                for p in parts:



                    if p.strip():



                        lines_out.append(f"{ind}{p.rstrip()}\\n")



                if _:



                    c = cmt if cmt.startswith("#") else ("#"+cmt)



                    lines_out.append(f"{ind}{c.strip()}\\n")



                changed = True



                continue







        ex = _expand_clause_oneliner(ln)



        if ex:



            lines_out.extend(ex); changed = True; continue







        exd = _expand_def_oneliner(ln)



        if exd:



            lines_out.extend(exd); changed = True; continue







        exc = _expand_class_oneliner(ln)



        if exc:



            lines_out.extend(exc); changed = True; continue







        lines_out.append(ln + "\\n")







    if lines_out and not lines_out[-1].endswith("\\n"):



        lines_out[-1] += "\\n"; changed = True



    return "".join(lines_out), changed







def should_skip(path: pathlib.Path) -> bool:



    parts = path.parts



    return any(p.startswith((".", "__pycache__", "venv", "env", "site-packages")) for p in parts)







def main():



    base = pathlib.Path(sys.argv[1] if len(sys.argv)>1 else ".").resolve()



    changed_files = 0



    for p in base.rglob("*.py"):



        if should_skip(p): continue



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



