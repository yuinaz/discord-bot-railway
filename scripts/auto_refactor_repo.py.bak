#!/usr/bin/env python3
from __future__ import annotations



# -*- coding: utf-8 -*-



"""



Auto refactor helper for common Ruff errors:



- E722: bare except -> `except Exception:`



- E701/E702: multiple statements / one-liners



    * Split `



    ` into separate lines (not inside strings / after comments)



    * Expand `if/for/while/with/try/except/else/elif` one-liners into blocks



Use with caution. It creates a backup .bak for each modified file.



"""








import os
import re
import sys

EXCLUDE_DIRS = {



    ".git",



    ".hg",



    ".mypy_cache",



    ".pytype",



    ".ruff_cache",



    ".venv",



    "venv",



    "env",



    "build",



    "dist",



    "__pycache__",



    "satpambot/vendor",



    "satpambot/third_party",



}







HEADERS = ("if", "elif", "else", "for", "while", "with", "try", "except", "finally", "def", "class")











def should_skip(path: str) -> bool:



    rp = path.replace("\\", "/")



    for ex in EXCLUDE_DIRS:



        if f"/{ex}/" in f"/{rp}/":



            return True



    return not path.endswith(".py")











def fix_bare_except(src: str) -> str:



    # except:\n  -> except Exception:\n



    return re.sub(r"(?m)^(\s*)except\s*:\s*(\r?\n)", r"\1except Exception:\2", src)











def split_semicolons_line(line: str) -> str:



    # Keep semicolons inside strings; stop at comments (#) that are not inside strings



    in_s = None  # quote char



    escaped = False



    out_parts = []



    cur = []



    i = 0



    while i < len(line):



        ch = line[i]



        if in_s:



            cur.append(ch)



            if escaped:



                escaped = False



            elif ch == "\\\\":



                escaped = True



            elif ch == in_s:



                in_s = None



        else:



            if ch in ("'", '"'):



                in_s = ch



                cur.append(ch)



            elif ch == "#":



                # rest is comment



                cur.extend(line[i:])



                i = len(line) - 1



            elif ch == ";":



                part = "".join(cur).rstrip()



                if part:



                    out_parts.append(part)



                cur = []



            else:



                cur.append(ch)



        i += 1



    rest = "".join(cur).rstrip()



    if rest:



        out_parts.append(rest)



    if not out_parts:



        return line



    # Rebuild with newline + same base indent



    base_indent = len(line) - len(line.lstrip(" "))



    indent = " " * base_indent



    return ("\n".join((indent + p.lstrip()) for p in out_parts)) + ("\n" if line.endswith("\n") else "")











def expand_header_one_liners(src: str) -> str:



    # Convert: "if cond: do()" -> "if cond:\n    do()"



    lines = src.splitlines(True)



    out = []



    for ln in lines:



        m = re.match(r"^(\s*)(if|elif|else|for|while|with|try|except(?:\s+[^\:]+)?|finally)\s*:\s*(\S.*)$", ln)



        if m:



            ind, head, tail = m.groups()



            # do not expand if tail starts with comment



            if tail.strip().startswith("#"):



                out.append(ln)



                continue



            # keep block header line



            out.append(f"{ind}{head}:\n")



            # body line indented +4



            out.append(f"{ind}    {tail}\n")



        else:



            out.append(ln)



    return "".join(out)











def auto_refactor_file(path: str) -> bool:



    with open(path, "r", encoding="utf-8", errors="ignore") as f:



        src = f.read()



    orig = src







    # 1) bare except



    src = fix_bare_except(src)



    # 2) split semicolons by line



    new_lines = []



    for ln in src.splitlines(True):



        if ";" in ln:



            new_lines.append(split_semicolons_line(ln))



        else:



            new_lines.append(ln)



    src = "".join(new_lines)



    # 3) expand one-liner headers



    src = expand_header_one_liners(src)







    if src != orig:



        bak = path + ".bak"



        try:



            os.replace(path, bak)



        except Exception:



            with open(bak, "w", encoding="utf-8") as bf:



                bf.write(orig)



        with open(path, "w", encoding="utf-8") as f:



            f.write(src)



        return True



    return False











def main(root: str = ".") -> int:



    changed = 0



    for dp, dn, fn in os.walk(root):



        for name in list(dn):



            if name in EXCLUDE_DIRS:



                dn.remove(name)



        for f in fn:



            p = os.path.join(dp, f)



            if should_skip(p):



                continue



            try:



                if auto_refactor_file(p):



                    print("refactored:", os.path.relpath(p, root))



                    changed += 1



            except Exception as e:



                print("skip error:", os.path.relpath(p, root), "->", e)



    print(f"Done. Files changed: {changed}")



    return 0











if __name__ == "__main__":



    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))



