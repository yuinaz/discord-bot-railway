
#!/usr/bin/env bash
set -euo pipefail
: "${UPSTASH_REDIS_REST_URL:?set this}"
: "${UPSTASH_REDIS_REST_TOKEN:?set this}"

AUTH="Authorization: Bearer ${UPSTASH_REDIS_REST_TOKEN}"

echo "[*] Baca nilai lama xp:bot:senior_total ..."
OLD=$(curl -s "$UPSTASH_REDIS_REST_URL/get/xp:bot:senior_total" -H "$AUTH" | sed -E 's/.*"result":"?([^"}]+)"?.*/\1/')
echo "    old = $OLD"

if [[ -z "$OLD" ]]; then
  echo "[!] Gagal membaca nilai lama."
  exit 1
fi

echo "[*] Tulis ke xp:bot:senior_total_v2 ..."
curl -s -X POST "$UPSTASH_REDIS_REST_URL/set/xp:bot:senior_total_v2/$OLD" -H "$AUTH"
echo
echo "[OK] Selesai."
