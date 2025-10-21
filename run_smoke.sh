#!/usr/bin/env bash
set -euo pipefail
# Ensure repo root is on PYTHONPATH
export PYTHONPATH="$(pwd)${PYTHONPATH:+:$PYTHONPATH}"
python tests/smoke_imports.py
python scripts/xp_test/simulate_senior_progress.py
python scripts/xp_test/whatif_label.py --xp 82290
echo "All smoke tests passed."
