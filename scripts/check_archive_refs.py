import re
import sys
from pathlib import Path

SKIP_DIRS = {



    ".git",



    ".github",



    ".venv",



    "venv",



    "__pycache__",



    "node_modules",



    "archive",



    "original_src",



    "dashboard/static/uploads",



    "scripts",



}



ALLOW_EXT = {".py", ".html", ".jinja", ".jinja2", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf"}



SKIP_FILES = {"README.md", "README.txt", ".gitignore", "check_archive_refs.py"}







PATS = [



    (r"archive[\\/]", "ref to archive/"),



    (r"original_src[\\/]", "ref to original_src/"),



    (r"requirements-windows\\.txt", "ref to req-windows"),



    (r"templates[\\/]+templates[\\/]+", "nested templates duplicate"),



]











def should_skip(path: Path) -> bool:



    # skip if any parent dir in SKIP_DIRS



    if any(part in SKIP_DIRS for part in (p.name for p in path.parents)):



        return True



    if path.name in SKIP_FILES:



        return True



    if path.suffix.lower() not in ALLOW_EXT:



        return True



    return False











issues = []



root = Path(".")



for f in root.rglob("*"):



    if not f.is_file():



        continue



    if should_skip(f):



        continue



    try:



        s = f.read_text(encoding="utf-8", errors="ignore")



    except Exception:



        continue



    for rx, desc in PATS:



        for m in re.finditer(rx, s, flags=re.I):



            ctx = s[max(0, m.start() - 80) : m.end() + 80].replace("\n", " ")



            issues.append((str(f).replace("\\", "/"), desc, ctx[:220]))







if issues:



    print("[!] Suspicious runtime references found:")



    for f, desc, ctx in issues:



        print(f"- {f} :: {desc} :: {ctx}")



    sys.exit(1)







print("[OK] No runtime refs to archive/original_src/req-windows/nested-templates.")



