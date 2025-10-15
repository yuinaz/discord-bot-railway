
"""
Lightweight post-start HTTP probe (optional).
Env: SANITY_BASE=http://127.0.0.1:10000 (default)
"""
import os, sys, urllib.request, json

BASE = os.getenv("SANITY_BASE", "http://127.0.0.1:10000")

def _get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=3) as r:
            return r.status, r.read()
    except Exception as e:
        return None, str(e).encode()

def main():
    checks = ["/healthz", "/uptime", "/api/live/stats"]
    ok = True
    for c in checks:
        st, body = _get(c)
        if st == 200:
            print(f"OK  : GET {c} :: 200")
        else:
            print(f"FAIL: GET {c} :: {st} :: {body[:120]!r}", file=sys.stderr)
            ok = False
    print("PASS" if ok else "FAIL")

if __name__ == "__main__":
    main()
