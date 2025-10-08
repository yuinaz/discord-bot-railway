#!/usr/bin/env bash
set -euo pipefail
PY=${PYTHON:-python}

echo "[use_groq_only] installing groq client & cleaning openai…"
$PY -m pip install --upgrade --no-cache-dir "groq>=0.13.0"
$PY -m pip uninstall -y openai || true

echo "[use_groq_only] done."
