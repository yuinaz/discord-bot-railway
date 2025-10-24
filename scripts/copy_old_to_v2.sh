
#!/usr/bin/env bash
set -euo pipefail
: "${UPSTASH_REDIS_REST_URL:?}"
: "${UPSTASH_REDIS_REST_TOKEN:?}"
AUTH="Authorization: Bearer ${UPSTASH_REDIS_REST_TOKEN}"

OLD=$(curl -s "$UPSTASH_REDIS_REST_URL/get/xp:bot:senior_total" -H "$AUTH" | sed -E 's/.*"result":"?([^"}]+)"?.*/\1/')
echo "old_key value: $OLD"
[[ -z "$OLD" ]] && { echo "[!] kosong"; exit 1; }
curl -s -X POST "$UPSTASH_REDIS_REST_URL/set/xp:bot:senior_total_v2/$OLD" -H "$AUTH"; echo
echo "[OK] copied old -> v2"
