
import os, json, sys, urllib.parse, urllib.request, argparse, re, hashlib

def norm(s): return re.sub(r"\s+"," ", s.strip().lower())
def sha1(s): return hashlib.sha1(s.encode()).hexdigest()

def upstash_get(url, token, key):
    if not (url and token): return None
    req = urllib.request.Request(f"{url.rstrip('/')}/get/{urllib.parse.quote(key, safe='')}",
                                 headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8") or "{}")
            return data.get("result")
    except Exception:
        return None

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", required=True)
    args = ap.parse_args()

    url = os.getenv("UPSTASH_REDIS_REST_URL")
    tok = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    ns = os.getenv("QNA_ANSWER_DEDUP_NS","qna:answered")
    key = f"{ns}:{sha1(norm(args.question))}"
    val = upstash_get(url,tok,key)
    print("[qna] key:", key)
    print("[qna] exists:", val is not None)
