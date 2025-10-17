#!/usr/bin/env python3
"""
smoke_xp_state.py  —  Upstash REST smoke tester (pipeline + safe fallback)

Usage:
  python patches/smoke_xp_state.py --url https://YOUR_ID.upstash.io --token TOKEN [--ladder TK]
  # or rely on env:
  export UPSTASH_REDIS_REST_URL=...
  export UPSTASH_REDIS_REST_TOKEN=...
  python patches/smoke_xp_state.py

This script sends a single /pipeline POST with three GET commands:
- GET xp:store
- GET xp:bot:senior_total
- GET xp:ladder:{ladder}

If /pipeline rejects the body (HTTP 400 parse error), it gracefully falls back to
single-command POSTs (["GET","key"]) so you can still verify connectivity.
"""
import os, json, argparse, urllib.request, urllib.error, sys, socket

def _norm_base(url: str) -> str:
    url = url.strip()
    if url.endswith("/"):
        url = url[:-1]
    return url

def post_json(url: str, token: str, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            txt = raw.decode("utf-8", errors="replace")
            try:
                return json.loads(txt), resp.getcode(), None
            except json.JSONDecodeError as e:
                return {"raw": txt}, resp.getcode(), None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": body}, e.code, e
    except urllib.error.URLError as e:
        return {"error": str(e)}, None, e

def single_get(base: str, token: str, key: str):
    # Upstash accepts POST with ["GET","key"]
    body = ["GET", key]
    res, code, err = post_json(base, token, body)
    return key, res, code, err

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.getenv("UPSTASH_REDIS_REST_URL"), help="Upstash REST base URL (no trailing slash)")
    ap.add_argument("--token", default=os.getenv("UPSTASH_REDIS_REST_TOKEN"), help="Upstash REST token")
    ap.add_argument("--ladder", default="TK", help="Active ladder phase key suffix (default: TK)")
    args = ap.parse_args()

    if not args.url or not args.token:
        print("[xp-smoke] ERROR: UPSTASH_REDIS_REST_URL / TOKEN belum diisi.", file=sys.stderr)
        sys.exit(2)

    base = _norm_base(args.url)

    print(f"[xp-smoke] Base URL : {base}")
    print(f"[xp-smoke] Token    : set({len(args.token)} chars)")

    # quick DNS sanity
    try:
        host = base.split("://",1)[1].split("/",1)[0]
        socket.getaddrinfo(host, 443)
    except Exception as e:
        print(f"ERROR: DNS gagal untuk host '{host}': {e}", file=sys.stderr)
        print("Hint: Periksa apakah UPSTASH_REDIS_REST_URL salah/ber-quote/ada spasi.", file=sys.stderr)
        sys.exit(3)

    keys = [
        "xp:store",
        "xp:bot:senior_total",
        f"xp:ladder:{args.ladder}",
    ]

    # 1) Try /pipeline with proper payload (top-level array of command arrays)
    pipeline_payload = [[ "GET", k ] for k in keys]
    res, code, err = post_json(f"{base}/pipeline", args.token, pipeline_payload)

    if code == 200 and isinstance(res, list):
        print("[xp-smoke] pipeline OK")
        for k, item in zip(keys, res):
            # each item is {"result": "..."} or {"error":"..."}
            val = item.get("result", item.get("error"))
            print(f"  - {k}: {val}")
        sys.exit(0)

    # If 400 with parse error → fallback to singles
    if code == 400:
        print(f"HTTP ERROR: 400 {res.get('error','')}")
        print("[xp-smoke] fallback: single POST per key…")

        ok = True
        for k in keys:
            key, r, c, e = single_get(base, args.token, k)
            if c == 200:
                print(f"  - {k}: {r.get('result', r)}")
            else:
                ok = False
                print(f"  - {k}: HTTP {c} {r}")
        sys.exit(0 if ok else 4)

    # Other errors
    print(f"[xp-smoke] unexpected HTTP {code}: {res}")
    sys.exit(5)

if __name__ == "__main__":
    main()
