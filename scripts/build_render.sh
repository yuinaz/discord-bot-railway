#!/usr/bin/env bash
set -euo pipefail

echo "[build_render] Python: $(python --version 2>&1)"
REQ_FILE="${REQUIREMENTS_FILE:-requirements.txt}"
echo "[build_render] Installing ${REQ_FILE} …"
python -m pip install -U pip setuptools wheel
python -m pip install -U -r "${REQ_FILE}" --upgrade-strategy eager

# optional hotfix step
if [[ -f scripts/apply_hotfixes.py ]]; then
  echo "[build_render] Hotfixes …"
  python scripts/apply_hotfixes.py || echo "[build_render] hotfix step non-fatal"
fi

# optional smoketest (non-fatal)
if [[ -f scripts/smoketest_render.py ]]; then
  echo "[build_render] Smoketest (non-fatal)…"
  python scripts/smoketest_render.py || echo "[build_render] smoketest non-fatal"
fi

echo "[build_render] Done. Start Command will run: python main.py"
