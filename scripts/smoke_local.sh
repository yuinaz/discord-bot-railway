#!/usr/bin/env bash
set -euo pipefail

detect_py() {
  if command -v python >/dev/null 2>&1; then echo "python"; return; fi
  if command -v py >/dev/null 2>&1; then echo "py -3"; return; fi
  if command -v python3 >/dev/null 2>&1; then echo "python3"; return; fi
  echo ""
}

CMD="$(detect_py)"
if [ -z "$CMD" ]; then
  echo "python not found in PATH. Install Python, or run via PowerShell: python scripts\\smoke_local_all.py"
  exit 127
fi

export PYTHONIOENCODING="utf-8"
export PYTHONUTF8="1"

eval "$CMD scripts/smoke_env.py" || true
eval "$CMD scripts/smoke_local_all.py"
