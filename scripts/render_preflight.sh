#!/usr/bin/env bash
set -euo pipefail

echo "[preflight] checking environment…"
for k in GROQ_API_KEY GOOGLE_API_KEY UPSTASH_REDIS_REST_URL UPSTASH_REDIS_REST_TOKEN; do
  v="${!k:-}"
  if [[ -z "$v" ]]; then echo "MISS $k"; else echo "OK   $k"; fi
done
bash scripts/smoke_providers.sh || true
