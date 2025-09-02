#!/usr/bin/env bash
set -Eeuo pipefail

echo "[build] Python: $(python --version 2>&1 || true)"
echo "[build] Pip   : $(python -m pip --version 2>&1 || true)"

echo "[build] Upgrading pip toolchain..."
python -m pip install -U pip setuptools wheel

if [[ ! -f requirements.txt ]]; then
  echo "[error] requirements.txt not found!"; exit 1
fi

echo "[build] Installing from requirements.txt (pinned, reproducible) ..."
python -m pip install -r requirements.txt

echo "[build] Verifying environment with pip check ..."
python -m pip check || { echo "[warn] pip check reported issues"; exit 1; }

echo "[build] Done."
