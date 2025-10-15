#!/usr/bin/env bash
set -euo pipefail

# Resolve repo root (this script is in ./scripts)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REQ="${ROOT}/requirements.latest.txt"

# Pick a Python launcher that exists (Git Bash/Windows friendly)
if command -v py >/dev/null 2>&1; then
  PY="py -3"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
elif command -v python >/dev/null 2>&1; then
  PY="python"
else
  echo "[use_latest] ERROR: Python not found in PATH."
  echo "             Add Python to PATH or run this script inside an activated venv."
  exit 1
fi

echo "[use_latest] using Python: $($PY - <<'PY'
import sys; print(sys.version.split()[0])
PY
)"

echo "[use_latest] installing from $(basename "$REQ" 2>/dev/null || echo 'requirements.txt (fallback)')"
$PY -m pip install --upgrade pip setuptools wheel

if [[ -f "$REQ" ]]; then
  $PY -m pip install -r "$REQ"
else
  $PY -m pip install -r "${ROOT}/requirements.txt"
fi

# Ensure translator libs are present at required minimums
$PY - <<'PYCODE'
import sys, subprocess
from importlib import metadata

def need(pkg, min_ver=None):
    try:
        v = metadata.version(pkg)
    except Exception:
        return True
    if not min_ver: return False
    from packaging.version import Version
    return Version(v) < Version(min_ver)

todo = []
if need("googletrans-py", "4.0.0"):
    todo.append("googletrans-py==4.0.0")
if need("deep-translator", "1.11.4"):
    todo.append("deep-translator==1.11.4")
if need("langdetect", "1.0.9"):
    todo.append("langdetect==1.0.9")

if todo:
    print("[use_latest] Installing/upgrading translator libs:", *todo)
    subprocess.check_call([sys.executable, "-m", "pip", "install", *todo])
else:
    print("[use_latest] translator libs OK")
PYCODE

echo "=== ENV CHECK ==="
$PY scripts/smoke_env.py || true
