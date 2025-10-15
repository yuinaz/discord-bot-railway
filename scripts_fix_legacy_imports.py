
"""
scripts_fix_legacy_imports.py

Cari dan perbaiki import warisan "modules" di dalam satpambot/**.py menjadi namespace yang benar:
- "from modules ..." -> "from satpambot.bot.modules ..."
- "import modules"   -> "import satpambot.bot.modules as modules"

Backup *.bak disimpan sebelum rewrite.

Usage:
  python scripts_fix_legacy_imports.py --root .
"""
import argparse, re
from pathlib import Path

PAT_FROM = re.compile(r'(^\s*)from\s+modules\b', re.MULTILINE)
PAT_IMPORT = re.compile(r'(^\s*)import\s+modules(\b|\s|$)', re.MULTILINE)

def fix_text(s: str):
    changed = False
    def repl_from(m):
        nonlocal changed
        changed = True
        return m.group(1) + 'from satpambot.bot.modules'
    def repl_import(m):
        nonlocal changed
        tail = m.group(1)  # includes space/newline boundary
        changed = True
        return m.group(1) + 'import satpambot.bot.modules as modules' + ('' if tail.strip() else tail)
    s2 = PAT_FROM.sub(repl_from, s)
    s2 = PAT_IMPORT.sub(repl_import, s2)
    return s2, changed

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='.', help='root folder project (yang berisi satpambot/)')
    args = ap.parse_args()
    root = Path(args.root).resolve()
    satpam = root / 'satpambot'
    if not satpam.exists():
        print('[ERR] folder satpambot/ tidak ditemukan di', root)
        return 2

    fixed = 0
    for p in satpam.rglob('*.py'):
        try:
            txt = p.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        new, changed = fix_text(txt)
        if changed:
            bak = p.with_suffix(p.suffix + '.bak')
            bak.write_text(txt, encoding='utf-8')
            p.write_text(new, encoding='utf-8')
            fixed += 1
            print('[FIX]', p.relative_to(root))
    print(f'[DONE] files fixed: {fixed}')

if __name__ == '__main__':
    raise SystemExit(main() or 0)
