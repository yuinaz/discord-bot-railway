
#!/usr/bin/env bash
set -euo pipefail

echo "== Groq test =="
resp="$(curl -sS -w $'\n%{http_code}' https://api.groq.com/openai/v1/chat/completions       -H "Authorization: Bearer ${GROQ_API_KEY:-}"       -H "Content-Type: application/json"       -d '{"model":"'"${GROQ_MODEL_ID:-llama-3.1-8b-instant}"'","messages":[{"role":"user","content":"ping?"}]}' )"
code="${resp##*$'\n'}"; body="${resp%$'\n'*}"
echo "Groq HTTP: $code"
if [ "$code" = "200" ]; then
  printf '%s' "$body" | tr -d '\n' | sed -n 's/.*"content":"\([^"]*\)".*/\1/p' | head -c 240; echo
else
  echo "$body"
fi

echo
echo "== Gemini test =="
key="${GEMINI_API_KEY:-${GOOGLE_API_KEY:-}}"
if [ -z "${key}" ]; then
  echo "GEMINI_API_KEY/GOOGLE_API_KEY missing"; exit 1
fi
resp="$(curl -sS -w $'\n%{http_code}'       "https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL_ID:-gemini-2.5-flash-lite}:generateContent?key=${key}"       -H "Content-Type: application/json"       -d '{"contents":[{"role":"user","parts":[{"text":"ping?"}]}]}' )"
code="${resp##*$'\n'}"; body="${resp%$'\n'*}"
echo "Gemini HTTP: $code"
if [ "$code" = "200" ]; then
  printf '%s' "$body" | tr -d '\n' | sed -n 's/.*"text":"\([^"]*\)".*/\1/p' | head -c 240; echo
else
  echo "$body"
fi
