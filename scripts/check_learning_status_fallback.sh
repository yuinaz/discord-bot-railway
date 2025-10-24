
#!/usr/bin/env bash
set -euo pipefail
: "${BASE:?Set BASE, e.g. https://satpambot-31l5.onrender.com}"
: "${UPSTASH_REDIS_REST_URL:?Set UPSTASH_REDIS_REST_URL}"
: "${UPSTASH_REDIS_REST_TOKEN:?Set UPSTASH_REDIS_REST_TOKEN}"
AUTH_HEADER=${AUTH:-}
AUTH="Authorization: Bearer ${UPSTASH_REDIS_REST_TOKEN}"

candidates=(
  "get/learning:status"
  "get/learning:status_json"
  "api/get/learning:status"
  "api/get/learning:status_json"
  "learning/status"
  "learning:status"
)

found=""
for p in "${candidates[@]}"; do
  url="$BASE/$p"
  code=$(curl -s -o /dev/null -w "%{http_code}" ${AUTH_HEADER:+-H "$AUTH_HEADER"} "$url" || true)
  if [[ "$code" == "200" ]]; then
    found="$p"
    break
  fi
done

if [[ -n "$found" ]]; then
  echo "[HTTP] $BASE/$found"
  curl -s ${AUTH_HEADER:+-H "$AUTH_HEADER"} "$BASE/$found"; echo
else
  echo "[Fallback Upstash] membaca learning:status & learning:status_json"
  curl -s "$UPSTASH_REDIS_REST_URL/get/learning:status" -H "$AUTH"; echo
  curl -s "$UPSTASH_REDIS_REST_URL/get/learning:status_json" -H "$AUTH"; echo
  echo "[Info XP] senior v2:"
  curl -s "$UPSTASH_REDIS_REST_URL/get/xp:bot:senior_total_v2" -H "$AUTH"; echo
fi
