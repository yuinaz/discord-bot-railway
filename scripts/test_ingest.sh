#!/usr/bin/env bash
set -euo pipefail
: "${RENDER_URL:?Set RENDER_URL to your Render service URL, e.g. https://your-app.onrender.com}"
: "${METRICS_INGEST_TOKEN:?Set METRICS_INGEST_TOKEN from Render env}"

curl -X POST "$RENDER_URL/dashboard/api/metrics-ingest"   -H "Content-Type: application/json"   -H "X-Token: $METRICS_INGEST_TOKEN"   -d '{"guilds":12,"members":4310,"online":523,"channels":184,"threads":9,"latency_ms":87}'
echo
echo "OK"
