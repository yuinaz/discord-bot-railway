# apply_flask_run_guard.py







# Idempotent patcher: gate all `app.run(...)` calls behind RUN_LOCAL_DEV==1







import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]







targets = [







    ROOT / "satpambot" / "dashboard" / "app_dashboard.py",







    ROOT / "satpambot" / "helpers" / "web_safe_start.py",







]







guard_file = ROOT / "satpambot" / "dashboard" / "dev_server_guard.py"























def ensure_import_os(lines: list[str]) -> list[str]:







    if any(re.match(r"^\s*import\s+os\b", ln) for ln in lines):







        return lines







    # Tambahkan setelah shebang/encoding/blank/import block paling awal







    insert_at = 0







    # skip shebang & encoding







    while insert_at < len(lines) and (







        lines[insert_at].startswith("#!") or "coding" in lines[insert_at] or lines[insert_at].strip() == ""







    ):







        insert_at += 1







    lines.insert(insert_at, "import os\n")







    return lines























def gate_app_run(text: str, path: Path) -> tuple[str, bool]:







    changed = False







    # pattern: leading indent + app.run(







    pat = re.compile(r"(?m)^(?P<ind>\s*)app\.run\s*\(")















    def repl(m):







        nonlocal changed







        changed = True







        ind = m.group("ind")







        return f'{ind}if os.getenv("RUN_LOCAL_DEV","0")=="1":\n{ind}    app.run('















    new_text, n = pat.subn(repl, text, count=1)  # only first occurrence per file







    # ensure import os exists if we inserted guard







    if changed:







        lines = new_text.splitlines(keepends=True)







        lines = ensure_import_os(lines)







        new_text = "".join(lines)







    return new_text, changed























def write_guard():







    guard_src = """# dev_server_guard: suppress Flask dev server in production







import os, logging







try:







    from flask import Flask







except Exception:  # pragma: no cover







    Flask = None















RUN_LOCAL_DEV_ON = os.getenv(\"RUN_LOCAL_DEV\", \"0\") == \"1\"















if Flask is not None and not RUN_LOCAL_DEV_ON:







    _orig_run = Flask.run







    def _noop_run(self, *a, **kw):







        logging.getLogger(\"dev_server_guard\").info(







            \"[dev-server-guard] Flask.run() suppressed (RUN_LOCAL_DEV!=1)\"







        )







        return None







    Flask.run = _noop_run  # type: ignore[attr-defined]







"""







    guard_file.parent.mkdir(parents=True, exist_ok=True)







    guard_file.write_text(guard_src, encoding="utf-8")







    print(f"[OK] wrote guard: {guard_file.relative_to(ROOT)}")























def main():







    write_guard()







    any_changed = False







    for p in targets:







        if not p.exists():







            print(f"[SKIP] not found: {p.relative_to(ROOT)}")







            continue







        src = p.read_text(encoding="utf-8")







        new, changed = gate_app_run(src, p)







        if changed:







            p.write_text(new, encoding="utf-8", newline="\n")







            print(f"[OK] patched: {p.relative_to(ROOT)}")







            any_changed = True







        else:







            print(f"[OK] no change needed: {p.relative_to(ROOT)}")







    if not any_changed:







        print("[INFO] nothing changed (already gated).")







    # Suggest import in main.py (optional)







    main_py = ROOT / "main.py"







    if main_py.exists():







        s = main_py.read_text(encoding="utf-8")







        marker = "satpambot.dashboard.dev_server_guard"







        if marker not in s:







            s = "import satpambot.dashboard.dev_server_guard  # noqa: F401\n" + s







            main_py.write_text(s, encoding="utf-8", newline="\\n")







            print("[OK] injected guard import at top of main.py")







        else:







            print("[OK] guard import already present in main.py")







    else:







        print("[WARN] main.py not found; add guard import manually if needed.")























if __name__ == "__main__":







    sys.exit(main())







