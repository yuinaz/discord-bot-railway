#!/usr/bin/env bash
set -Eeuo pipefail
echo "[build_render] Python: $(python -V)"
if [[ -f requirements.txt ]]; then
  echo "[build_render] Installing requirements.txt …"
  pip install --no-cache-dir -r requirements.txt
fi
echo "[build_render] Ensuring openai>=1,<2 and python-dotenv…"
pip install --no-cache-dir "openai>=1.52,<2" "python-dotenv>=1.0,<2" || true
echo "[build_render] Hotfix OpenAI v1 (non-fatal)…"
python scripts/apply_hotfixes.py || echo "[warn] hotfix failed (continuing)"
echo "[build_render] Smoketest (non-fatal)…"
python scripts/smoketest_render.py || echo "[warn] smoketest failed (continuing)"
echo "[build_render] Done. Start Command will run: python main.py"
