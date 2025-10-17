#!/usr/bin/env bash
set -e
: "${GROQ_API_KEY:?need GROQ_API_KEY}"
curl -sS https://api.groq.com/openai/v1/chat/completions   -H "Authorization: Bearer $GROQ_API_KEY" -H "Content-Type: application/json"   -d '{"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":"ping?"}]}' | jq -r '.choices[0].message.content' || true

: "${GEMINI_API_KEY:?need GEMINI_API_KEY}"
curl -sS "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key=$GEMINI_API_KEY"   -H "Content-Type: application/json"   -d '{"contents":[{"role":"user","parts":[{"text":"ping?"}]}]}' | jq -r '.candidates[0].content.parts[0].text' || true
