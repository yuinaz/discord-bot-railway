
#!/usr/bin/env bash
set -euo pipefail
: "${BASE:?Set BASE, e.g. https://satpambot-31l5.onrender.com}"
AUTH_HEADER=${AUTH:-}

paths=(
  "healthz"
  "get/learning:status"
  "get/learning:status_json"
  "api/get/learning:status"
  "api/get/learning:status_json"
  "learning/status"
  "learning:status"
)

printf "BASE=%s\n" "$BASE"
if [[ -n "$AUTH_HEADER" ]]; then
  printf "AUTH=%s\n" "$AUTH_HEADER"
else
  echo "AUTH not set (will call without Authorization header)"
fi
echo "----"

for p in "${paths[@]}"; do
  url="$BASE/$p"
  code=$(curl -s -o /dev/null -w "%{http_code}" ${AUTH_HEADER:+-H "$AUTH_HEADER"} "$url")
  echo "$code  $url"
done
