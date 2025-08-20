#!/usr/bin/env bash
set -euo pipefail

# ===== Render cached build for Python =====
# - Uses pip cache between deploys (Render Build Cache)
# - Skips reinstall when requirements.txt hash is unchanged

CACHE_DIR=".pip-cache"
REQ_HASH_FILE=".render-requirements.hash"

echo "==> Python $(python --version 2>&1)"
python -m pip install -U pip wheel >/dev/null

if [[ ! -f requirements.txt ]]; then
  echo "ERROR: requirements.txt not found at project root"
  exit 1
fi

# compute hash of requirements.txt
REQ_HASH="$(sha256sum requirements.txt | awk '{print $1}')"

if [[ -f "${REQ_HASH_FILE}" ]] && [[ "$(cat "${REQ_HASH_FILE}")" == "${REQ_HASH}" ]]; then
  echo "==> requirements.txt unchanged, SKIP pip install (using cache)."
  # still ensure cache dir exists for future builds
  mkdir -p "${CACHE_DIR}"
else
  echo "==> requirements.txt changed/new, installing dependencies (cached)..."
  python -m pip install --cache-dir "${CACHE_DIR}" -r requirements.txt
  echo "${REQ_HASH}" > "${REQ_HASH_FILE}"
fi

# do not fail build on optional dependency warnings
python -m pip check || true
echo "==> Build finished (cached)."
