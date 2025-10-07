import os
from glob import glob

try:
    from jinja2 import Environment, FileSystemLoader
    def check_jinja(base):
        env = Environment(loader=FileSystemLoader(base))
        for p in glob(os.path.join(base, "**","*.html"), recursive=True):
            rel = os.path.relpath(p, base)
            try:
                env.get_template(rel)
            except Exception as e:
                print("[JINJA ERROR]", rel, "->", e)
                raise
        print("[OK] Jinja templates compile")
except Exception:
    def check_jinja(base):
        print("[SKIP] jinja2 not installed")

def check_sql(base):
    for p in glob(os.path.join(base, "**","*.sql"), recursive=True):
        s = open(p,"r",encoding="utf-8",errors="ignore").read()
        if s.count("\"") % 2 != 0 or s.count("'") % 2 != 0:
            raise SystemExit(f"[SQL ERROR] likely unclosed quotes: {p}")
    print("[OK] SQL strings balanced")

def main():
    if os.path.exists("satpambot/dashboard/templates"):
        check_jinja("satpambot/dashboard/templates")
    if os.path.exists("sql"):
        check_sql("sql")

if __name__ == "__main__":
    main()
