#!/usr/bin/env bash
set -euo pipefail
PROMPT="${1:-apa itu cache?}"
echo "[SMOKE] prompt: $PROMPT"
if [ -n "${GEMINI_API_KEY:-${GOOGLE_API_KEY:-}}" ]; then
  KEY="${GEMINI_API_KEY:-${GOOGLE_API_KEY}}"
  echo "[TRY] Gemini…"
  RES=$(curl -sS -X POST     -H "Content-Type: application/json"     -H "x-goog-api-key: ${KEY}"     -d "{"contents":[{"parts":[{"text":"$PROMPT"}]}]}"     "https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL:-gemini-2.5-flash-lite}:generateContent" || true)
  if echo "$RES" | jq -e '.candidates[0].content.parts[0].text' >/dev/null 2>&1; then
    echo "[OK] Answer by GEMINI"
    echo "$RES" | jq -r '.candidates[0].content.parts[0].text'
    exit 0
  fi
fi
if [ -n "${GROQ_API_KEY:-}" ]; then
  echo "[TRY] Groq…"
  RES=$(curl -sS -X POST "https://api.groq.com/openai/v1/chat/completions"     -H "Authorization: Bearer ${GROQ_API_KEY}"     -H "Content-Type: application/json"     -d "{"model":"${LLM_GROQ_MODEL:-llama-3.1-8b-instant}","messages":[{"role":"user","content":"$PROMPT"}],"temperature":0.3}" || true)
  if echo "$RES" | jq -e '.choices[0].message.content' >/dev/null 2>&1; then
    echo "[OK] Answer by GROQ"
    echo "$RES" | jq -r '.choices[0].message.content'
    exit 0
  fi
fi
echo "[FAIL] Both providers unavailable or returned unexpected payload."
exit 2
