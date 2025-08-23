#!/usr/bin/env bash
set -euo pipefail
f="requirements.txt"
[ -f "$f" ] || { echo "requirements.txt not found"; exit 1; }
if ! grep -qi '^imagehash\b' "$f"; then
  printf "\nImageHash>=4.3\n" >> "$f"
  echo "Added ImageHash>=4.3"
else
  echo "ImageHash already present"
fi
