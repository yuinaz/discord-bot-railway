
#!/usr/bin/env bash
set -euo pipefail
: "${BASE:=}"
: "${AUTH:=}"

if [[ -z "${BASE}" || -z "${AUTH}" ]]; then
  echo "[!] BASE atau AUTH kosong."
  echo "    Contoh:"
  echo "      export BASE="https://satpambot-31l5.onrender.com""
  echo "      export AUTH="Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN""
  exit 1
fi

echo "# status label KULIAH"
curl -s -H "$AUTH" "$BASE/get/learning:status"; echo
curl -s -H "$AUTH" "$BASE/get/learning:status_json"; echo
