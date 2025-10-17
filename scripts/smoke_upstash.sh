#!/usr/bin/env bash
set -e
: "${UPSTASH_REDIS_REST_URL:?url}"
: "${UPSTASH_REDIS_REST_TOKEN:?token}"
H="Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN"

echo "# xp:store updated_at:"
curl -s "$UPSTASH_REDIS_REST_URL/get/xp:store" -H "$H" | jq -r '.result' | jq -r '.updated_at' || true

echo "# senior_total:"
curl -s "$UPSTASH_REDIS_REST_URL/get/xp:bot:senior_total" -H "$H" | jq -r '.result' || true

echo "# TK ladder L1:"
curl -s "$UPSTASH_REDIS_REST_URL/get/xp:ladder:TK" -H "$H" | jq -r '.result' || true
