
import os, json, sys, re, time, hashlib
import urllib.parse, urllib.request

def _env(k, d=None): return os.getenv(k, d)

def _upstash_get(url, token, key):
    if not (url and token): return None
    full = f"{url.rstrip('/')}/get/{urllib.parse.quote(key, safe='')}"
    req = urllib.request.Request(full, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8") or "{}")
            return data.get("result")
    except Exception as e:
        return None

def _probe_int(val):
    try:
        return int(val)
    except Exception:
        try:
            if isinstance(val, str) and val.isdigit():
                return int(val)
        except Exception:
            pass
    return None

def main():
    url = _env("UPSTASH_REDIS_REST_URL")
    tok = _env("UPSTASH_REDIS_REST_TOKEN")

    senior_key = _env("XP_SENIOR_KEY") or _env("SENIOR_XP_KEY") or "xp:bot:senior_total"
    tk_key = _env("TK_XP_KEY") or "xp:bot:tk_total"
    status_key = _env("LEARNING_STATUS_KEY", "learning:status")
    status_json_key = _env("LEARNING_STATUS_JSON_KEY", "learning:status_json")
    phase_key = _env("LEARNING_PHASE_KEY", "learning:phase")

    print("[upstash] url:", url)
    print("[xp] keys:", senior_key, tk_key)
    print("[learning] keys:", status_key, status_json_key, phase_key)

    s = _upstash_get(url, tok, senior_key)
    t = _upstash_get(url, tok, tk_key)
    js = _upstash_get(url, tok, status_json_key)
    st = _upstash_get(url, tok, status_key)
    ph = _upstash_get(url, tok, phase_key)

    print("\n[values]")
    print(" senior_total =", s)
    print(" tk_total     =", t)
    print(" status       =", st)
    print(" status_json  =", js)
    print(" phase        =", ph)

    ok = True
    if s is None:
        print(" ! senior_total missing"); ok = False
    elif _probe_int(s) is None:
        print(" ! senior_total not int-like"); ok = False

    if js:
        try:
            obj = json.loads(js)
            if not isinstance(obj, dict) or "label" not in obj or "percent" not in obj:
                print(" ! status_json malformed")
                ok = False
        except Exception:
            print(" ! status_json not json"); ok = False

    print("\n[result] XP store:", "OK ✅" if ok else "Check ❗")
    if ok and _probe_int(s) is not None:
        v = int(_probe_int(s))
        print(f" tip: XP senior_total int = {v:,}")

if __name__ == "__main__":
    main()
