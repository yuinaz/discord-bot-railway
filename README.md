# Patch: Upstash ENV bridge + Force Senior Progress

## What this does
1. **a06_upstash_env_bridge_overlay.py**
   - Maps common Render/Upstash ENV names to those expected by the bot:
     - `UPSTASH_REDIS_REST_URL` -> `UPSTASH_REST_URL`
     - `UPSTASH_REDIS_REST_TOKEN` -> `UPSTASH_REST_TOKEN`
     - also supports `UPSTASH_KV_REST_*` and generic `UPSTASH_URL/TOKEN`.
   - Sets `UPSTASH_ENABLE=1` if not present.
   - Logs the effective URL/token presence for verification.

2. **a25_force_senior_progress_overlay.py**
   - Forces preferred track to **senior**.
   - Best-effort patch for curriculum split and reporter (if present).

## How to install
- Extract this zip at the repo root so paths match.
- Deploy/run. In logs you should see:
  - `[upstash-overlay] effective url=... token=set`
  - Bridge log should change to `upstash=True`.

## Rollback
- Remove these two overlay files and redeploy.
