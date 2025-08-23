#!/usr/bin/env bash
set -euo pipefail
: "${RENDER_URL:?Set RENDER_URL to your Render service URL}"
FILE="${1:-}"
if [[ -z "$FILE" ]]; then
  echo "Usage: $0 /path/to/image.png"
  exit 1
fi

curl -X POST "$RENDER_URL/dashboard/api/phash/upload"   -H "Content-Type: multipart/form-data"   -F "file=@${FILE}"
echo
