#!/usr/bin/env bash
set -euo pipefail

echo "== SatpamBot GitHub Cleanup Kit v1 =="

test -d "satpambot" || { echo "!! Jalankan dari root repo (harus ada folder satpambot)"; exit 1; }

python - <<'PY'
import shutil, pathlib
src = pathlib.Path("patch")/"satpambot"
dst = pathlib.Path("satpambot")
files = [
  "dashboard/static/css/login_exact.css",
  "dashboard/themes/gtake/templates/login.html",
  "dashboard/templates/security.html",
  "bot/modules/discord_bot/cogs/live_metrics_push.py",
  "bot/modules/discord_bot/cogs/sticky_status.py",
  "dashboard/log_mute_healthz.py",
]
for rel in files:
  s = src / rel
  d = dst / rel
  d.parent.mkdir(parents=True, exist_ok=True)
  shutil.copy2(s, d)
  print("[copy]", rel)
PY

for f in \
  "satpambot/bot/modules/discord_bot/cogs/status_sticky_patched.py" \
  "satpambot/bot/modules/discord_bot/cogs/sticky_guard.py"
do
  if [ -f "$f" ]; then
    mv -f "$f" "$f.disabled"
    echo "[rename] $f -> $f.disabled"
  fi
done

if git ls-files --error-unmatch login.html.patch >/dev/null 2>&1; then
  git rm -f login.html.patch
  echo "[git rm] login.html.patch"
else
  rm -f login.html.patch 2>/dev/null || true
fi

python - <<'PY'
from pathlib import Path
p = Path("satpambot/dashboard/webui.py")
txt = p.read_text(encoding="utf-8")
orig = txt
imp = "import satpambot.dashboard.log_mute_healthz  # noqa: F401"
if imp not in txt:
    lines = txt.splitlines()
    lines.insert(1, imp)
    txt = "\n".join(lines)
sec_def = '@bp.get("/security")'
if sec_def not in txt:
    txt += "\n\n@bp.get(\"/security\")\ndef security():\n    from flask import current_app, render_template\n    cfg = current_app.config.get(\"UI_CFG\") or {}\n    return render_template(\"security.html\", title=\"Security\", cfg=cfg)\n"
met_def = '@bp.get("/dashboard/api/metrics")'
if met_def not in txt:
    txt += "\n\n@bp.get(\"/dashboard/api/metrics\")\ndef dashboard_metrics():\n    from flask import jsonify\n    try:\n        from satpambot.dashboard import live_store as _ls\n        data = getattr(_ls, \"STATS\", {}) or {}\n        return jsonify(data)\n    except Exception:\n        return jsonify({\"member_count\": 0, \"online_count\": 0, \"latency_ms\": 0, \"cpu\": 0.0, \"ram\": 0.0})\n"
if txt != orig:
    Path(str(p)+".bak").write_text(orig, encoding="utf-8")
    p.write_text(txt, encoding="utf-8")
    print("[patch] webui.py updated (+ .bak)")
else:
    print("[patch] webui.py unchanged")
PY

if [ -f "requirements.txt" ] && ! grep -qi '^psutil' requirements.txt; then
  echo "psutil>=5.9" >> requirements.txt
  echo "[req] psutil added"
fi

echo "== Cleanup done. Commit recommended =="
