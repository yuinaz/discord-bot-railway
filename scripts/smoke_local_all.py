#!/usr/bin/env python
import os, sys, subprocess, time
from pathlib import Path

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[1]

PY = sys.executable  # use the same Python env
ENV = os.environ.copy()
ENV["PYTHONIOENCODING"] = "utf-8"
ENV.setdefault("PYTHONUTF8", "1")  # force UTF-8 mode when possible

SCRIPTS = [
    "scripts/smoketest_render.py",
    "scripts/smoketest_all.py",
    "scripts/smoke_cogs.py",
]

def run_one(script_path: str):
    print(f"\n==> RUN: {script_path}")
    start = time.time()
    cmd = [PY, script_path]
    p = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=ENV,
    )
    dur = time.time() - start
    if p.stdout:
        print(p.stdout, end="")
    if p.stderr:
        print(p.stderr, file=sys.stderr, end="")
    status = "OK" if p.returncode == 0 else "FAIL"
    print(f"-- {status} ({dur:.1f}s)")
    return p.returncode

def main():
    print(f"[smoke_local_all] Python: {sys.version.split()[0]}")
    print(f"[smoke_local_all] Repo: {REPO_ROOT}")
    rc = 0
    for s in SCRIPTS:
        path = REPO_ROOT / s
        if not path.exists():
            print(f"[WARN] Missing: {s}")
            continue
        if run_one(str(path)) != 0:
            rc = 1
    print("\n=== SUMMARY ===")
    print("All OK" if rc == 0 else "FAIL: see log above")
    raise SystemExit(rc)

if __name__ == "__main__":
    main()
