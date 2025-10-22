#!/usr/bin/env bash
set -euo pipefail
: "${UPSTASH_REDIS_REST_URL:?}"
: "${UPSTASH_REDIS_REST_TOKEN:?}"
KEY="${XP_SENIOR_KEY:-xp:bot:senior_total_v2}"
echo "[upstash] url: $UPSTASH_REDIS_REST_URL"
echo "[xp key]  $KEY"
echo
echo "[1/3] BEFORE"
curl -sS -X POST "$UPSTASH_REDIS_REST_URL/pipeline" \
  -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" \
  -H "Content-Type: application/json" \
  -d "[[\"GET\",\"$KEY\"]]"
echo
echo
echo "==> Kirim 1 chat di channel XP, tunggu 15 detik..."
sleep 15
echo
echo "[2/3] AFTER"
curl -sS -X POST "$UPSTASH_REDIS_REST_URL/pipeline" \
  -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" \
  -H "Content-Type: application/json" \
  -d "[[\"GET\",\"$KEY\"]]"
echo
