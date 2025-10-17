#!/usr/bin/env bash
# Smoke test untuk Groq & Gemini
# Kebutuhan env: GROQ_API_KEY, GOOGLE_API_KEY
set -Eeuo pipefail
IFS=$'\n\t'

have() { command -v "$1" >/dev/null 2>&1; }

GROQ_URL="https://api.groq.com/openai/v1/chat/completions"
GEM_URL="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key=${GOOGLE_API_KEY:-}"

TMPDIR="${TMPDIR:-/tmp}"
GROQ_JSON="$TMPDIR/groq.json"
GEM_JSON="$TMPDIR/gem.json"

echo "== Groq test =="
if [[ -z "${GROQ_API_KEY:-}" ]]; then
  echo "Groq API key missing (set GROQ_API_KEY)."
else
  groq_http=$(
    curl -sS -o "$GROQ_JSON" -w "%{http_code}" "$GROQ_URL" \
      -H "Authorization: Bearer ${GROQ_API_KEY}" \
      -H "Content-Type: application/json" \
      -d '{"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":"Ping?"}]}'
  )
  echo "Groq HTTP: $groq_http"
  if [[ "$groq_http" == "200" ]]; then
    if have jq; then
      jq -r '.choices[0].message.content // empty' "$GROQ_JSON"
    elif have python; then
      python - "$GROQ_JSON" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))["choices"][0]["message"]["content"])
PY
    elif have powershell; then
      powershell -NoProfile -Command "(Get-Content $env:TMP/groq.json | ConvertFrom-Json).choices[0].message.content"
    else
      echo "(raw)"; cat "$GROQ_JSON"
    fi
  else
    cat "$GROQ_JSON"
  fi
fi

echo
echo "== Gemini test =="
if [[ -z "${GOOGLE_API_KEY:-}" ]]; then
  echo "Gemini API key missing (set GOOGLE_API_KEY)."
else
  gem_http=$(
    curl -sS -o "$GEM_JSON" -w "%{http_code}" "$GEM_URL" \
      -H "Content-Type: application/json" \
      -d '{"contents":[{"role":"user","parts":[{"text":"Ping?"}]}]}'
  )
  echo "Gemini HTTP: $gem_http"
  if [[ "$gem_http" == "200" ]]; then
    if have jq; then
      jq -r '.candidates[0].content.parts[0].text // empty' "$GEM_JSON"
    elif have python; then
      python - "$GEM_JSON" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
print(d["candidates"][0]["content"]["parts"][0]["text"])
PY
    elif have powershell; then
      powershell -NoProfile -Command "(ConvertFrom-Json (Get-Content $env:TMP/gem.json)).candidates[0].content.parts[0].text"
    else
      echo "(raw)"; cat "$GEM_JSON"
    fi
  else
    cat "$GEM_JSON"
  fi
fi
