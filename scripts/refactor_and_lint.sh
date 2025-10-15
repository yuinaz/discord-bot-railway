#!/usr/bin/env bash
set -euo pipefail

# 1) run auto-refactor (creates .bak backups)
python scripts/auto_refactor_repo.py .

# 2) format + fixes
if python -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('ruff') else 1)"; then
  echo "== Ruff format =="
  python -m ruff format . --config ruff.toml || true
  echo "== Ruff fix (safe) =="
  python -m ruff check . --config ruff.toml --fix || true
else
  echo "[!] ruff not found; install with: python -m pip install -U ruff"
fi

echo "[✓] Auto-refactor done. Review *.bak diffs if needed."
