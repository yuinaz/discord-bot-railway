
#!/usr/bin/env bash
set -euo pipefail
: "${UPSTASH_REDIS_REST_URL:?}"
: "${UPSTASH_REDIS_REST_TOKEN:?}"
AUTH="Authorization: Bearer ${UPSTASH_REDIS_REST_TOKEN}"

V2=$(curl -s "$UPSTASH_REDIS_REST_URL/get/xp:bot:senior_total_v2" -H "$AUTH" | sed -E 's/.*"result":"?([^"}]+)"?.*/\1/')
echo "v2_key value: $V2"
[[ -z "$V2" ]] && { echo "[!] kosong"; exit 1; }
curl -s -X POST "$UPSTASH_REDIS_REST_URL/set/xp:bot:senior_total/$V2" -H "$AUTH"; echo
echo "[OK] copied v2 -> old"
