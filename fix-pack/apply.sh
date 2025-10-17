
#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo_root="${1:-.}"
echo "[fix-pack] applying drop-in cogs…"
mapfile -t files < <(cd "$here/../dropins" && find . -type f -name '*.py' | sed 's#^./##')
for rel in "${files[@]}"; do
  src="$here/../dropins/$rel"
  dst="$repo_root/$rel"
  mkdir -p "$(dirname "$dst")"
  cp -f "$src" "$dst"
  echo " - installed $rel"
done
if [ -f "$repo_root/requirements.txt" ]; then
  if ! grep -qi '^PyYAML' "$repo_root/requirements.txt"; then
    echo "PyYAML>=6.0.2" >> "$repo_root/requirements.txt"
    echo " - appended PyYAML to requirements.txt"
  else
    echo " - PyYAML already in requirements.txt"
  fi
fi
echo "[fix-pack] done."
