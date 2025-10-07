#!/usr/bin/env bash
set -euo pipefail
REQ=${REQ:-requirements.latest.txt}
if [[ ! -f "$REQ" ]]; then
  echo "File $REQ tidak ditemukan"; exit 1
fi
echo "[use_latest] installing from $REQ"
python -m pip install -U pip setuptools wheel
python -m pip install -U -r "$REQ" --upgrade-strategy eager
if [[ -f scripts/smoke_local.sh ]]; then bash scripts/smoke_local.sh || true; fi
