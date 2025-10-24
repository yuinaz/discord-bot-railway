#!/usr/bin/env python
import argparse, json, sys, re, time
from pathlib import Path

def load_any(p: Path):
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, list): return [str(x).strip() for x in data if isinstance(x, str)]
    if isinstance(data, dict): return [str(x).strip() for x in (data.get("seeds") or []) if isinstance(x, str)]
    raise ValueError("Unsupported JSON structure")

def save_like_target(p: Path, original_text: str, merged: list[str]):
    try:
        obj = json.loads(original_text)
        if isinstance(obj, dict):
            obj["seeds"] = merged
            p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8"); return
    except Exception: pass
    p.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

def norm(s: str)->str:
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[.?!、。…]+$", "", s)
    return s

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=Path, default=Path("data/config/qna_topics.json"))
    ap.add_argument("--add",    type=Path, default=Path("data/config/qna_topics_additions.json"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if not args.target.exists(): print(f"[!] target missing: {args.target}"); sys.exit(2)
    if not args.add.exists():    print(f"[!] additions missing: {args.add}"); sys.exit(2)

    tgt_text = args.target.read_text(encoding="utf-8")
    cur = load_any(args.target); add = load_any(args.add)
    seen = {norm(x): x for x in cur}; added = 0
    for q in add:
        k = norm(q)
        if k in seen: continue
        seen[k] = q; added += 1
    merged = list(seen.values())
    print(f"[merge] current={len(cur)} add={len(add)} -> unique={len(merged)} (added {added})")
    if args.dry_run: return
    ts = time.strftime("%Y%m%d-%H%M%S")
    backup = args.target.with_suffix(args.target.suffix + f".bak-{ts}")
    backup.write_text(tgt_text, encoding="utf-8")
    save_like_target(args.target, tgt_text, merged)
    print(f"[merge] wrote {args.target.name} (backup {backup.name})")

if __name__ == "__main__":
    main()
