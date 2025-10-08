#!/usr/bin/env bash
set -euo pipefail

PY_BIN="${PY_BIN:-python}"
if command -v py >/dev/null 2>&1; then PY_BIN="py -3"; fi
if command -v python3 >/dev/null 2>&1; then PY_BIN="python3"; fi

if [[ -f requirements.latest.txt ]]; then
  echo "[build_render] installing requirements.latest.txt"
  $PY_BIN -m pip install --upgrade pip
  $PY_BIN -m pip install -r requirements.latest.txt
elif [[ -f requirements.txt ]]; then
  echo "[build_render] installing requirements.txt"
  $PY_BIN -m pip install -r requirements.txt
fi

echo "[build_render] smoke checks"
$PY_BIN scripts/smoke_env.py || true
$PY_BIN scripts/smoke_translator.py || true
$PY_BIN scripts/smoke_warn_blocker.py || true
echo "[build_render] done"
