#!/usr/bin/env bash
set -euo pipefail

echo "[preflight] checking environment…"
req=(GROQ_API_KEY GOOGLE_API_KEY UPSTASH_REDIS_REST_URL UPSTASH_REDIS_REST_TOKEN)
for k in "${req[@]}"; do
  v="${!k:-}"
  if [ -n "$v" ]; then
    echo "OK   $k"
  else
    echo "MISS $k"
  fi
done

bash scripts/smoke_providers.sh || true
