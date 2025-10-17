
#!/usr/bin/env bash
set -euo pipefail
h="Authorization: Bearer ${UPSTASH_REDIS_REST_TOKEN:-}"
echo "# xp:store"
curl -s "$UPSTASH_REDIS_REST_URL/get/xp:store" -H "$h" | head -c 160; echo
echo "# senior_total"
curl -s "$UPSTASH_REDIS_REST_URL/get/xp:bot:senior_total" -H "$h"; echo
echo "# ladder TK"
curl -s "$UPSTASH_REDIS_REST_URL/get/xp:ladder:TK" -H "$h"; echo
