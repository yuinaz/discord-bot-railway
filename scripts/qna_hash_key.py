
import os, re, argparse, hashlib
def norm(s): return re.sub(r"\s+"," ", s.strip().lower())
def sha1(s): return hashlib.sha1(s.encode()).hexdigest()
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", required=True)
    args = ap.parse_args()
    ns = os.getenv("QNA_ANSWER_DEDUP_NS","qna:answered")
    h = sha1(norm(args.question))
    print(f"{ns}:{h}")
