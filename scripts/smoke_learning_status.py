#!/usr/bin/env python3
import os, json, argparse, sys

def _to_windows_drive_if_gitbash_style(path: str) -> str:
    import re, os
    if not path: return path
    m = re.match(r"^/([a-zA-Z])/(.*)$", path.replace('\\','/'))
    if m:
        drive = m.group(1).upper()
        rest = m.group(2).replace('/', os.sep)
        return f"{drive}:{os.sep}{rest}"
    return path

def _repo_root_candidates(script_dir: str):
    # walk upward from script dir
    import os
    cur = os.path.abspath(script_dir)
    for _ in range(12):
        yield cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    # also try from CWD
    cur = os.path.abspath(os.getcwd())
    for _ in range(10):
        yield cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break

def _resolve_neurolite_default(script_dir: str):
    # Prefer user's canonical location: data/neuro-lite/ladder.json under repo root
    import os
    for root in _repo_root_candidates(script_dir):
        cand = os.path.join(root, "data", "neuro-lite", "ladder.json")
        if os.path.exists(cand):
            return os.path.abspath(cand)
    return None

def _resolve_ladder_path(cli_path: str, script_dir: str):
    import os
    # 0) explicit CLI
    if cli_path:
        cand = _to_windows_drive_if_gitbash_style(cli_path)
        if os.path.isabs(cand) and os.path.exists(cand):
            return os.path.abspath(cand)
        rel = os.path.abspath(cand)
        if os.path.exists(rel):
            return rel
        rel2 = os.path.abspath(os.path.join(script_dir, cand))
        if os.path.exists(rel2):
            return rel2
    # 1) env var
    envp = os.getenv("LADDER_FILE")
    if envp:
        envp2 = _to_windows_drive_if_gitbash_style(envp)
        if os.path.exists(envp2):
            return os.path.abspath(envp2)
    # 2) neuro-lite default
    nl = _resolve_neurolite_default(script_dir)
    if nl:
        return nl
    # 3) repo-root ladder.json
    for root in _repo_root_candidates(script_dir):
        cand = os.path.join(root, "ladder.json")
        if os.path.exists(cand):
            return os.path.abspath(cand)
    return None


SENIOR_PHASES = ["SMP", "SMA", "KULIAH"]
JUNIOR_PHASES = ["TK", "SD"]

def _parse_stage_key(k: str) -> int:
    k = str(k).strip().upper()
    for p in ("L","S"):
        if k.startswith(p):
            try:
                return int(k[len(p):])
            except Exception:
                pass
    try:
        return int(k)
    except Exception:
        return 999999

def _load_ladders(path: str):
    with open(path, "r", encoding="utf-8") as f:
        j = json.load(f)
    ladders = {}
    for domain in ("junior","senior"):
        d = j.get(domain) or {}
        for phase, stages in d.items():
            ladders[phase] = {str(k): int(v) for k,v in stages.items()}
    return ladders

def _compute(domain_phases, total, ladders):
    spent = 0
    def order(d):
        return sorted(d.items(), key=lambda kv: _parse_stage_key(kv[0]))
    for phase in domain_phases:
        chunks = ladders.get(phase, {})
        for (stage, need) in order(chunks):
            need = max(1, int(need))
            have_in_stage = max(0, total - spent)
            if have_in_stage < need:
                pct = 100.0 * (have_in_stage / float(need))
                rem = max(0, need - have_in_stage)
                return (f"{phase}-S{_parse_stage_key(stage)}", round(pct,1), rem)
            spent += need
    last = domain_phases[-1]
    last_idx = len(order(ladders.get(last, {"S1":1})))
    return (f"{last}-S{last_idx}", 100.0, 0)

def main(domain, ladder_cli_path):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ladder_path = _resolve_ladder_path(ladder_cli_path, script_dir)
    if not ladder_path:
        print("ERROR: ladder.json not found. Pass --ladder <path> or set LADDER_FILE; default path 'data/neuro-lite/ladder.json' also tried.", file=sys.stderr)
        sys.exit(2)
    ladders = _load_ladders(ladder_path)
    phases = SENIOR_PHASES if domain=="senior" else JUNIOR_PHASES
    samples = [0, 500, 1000, 1499, 1500, 3000, 9999, 10000, 25000, 60000, 82000, 120000]
    print(f"Domain: {domain} | ladder={ladder_path}")
    for s in samples:
        label, pct, rem = _compute(phases, s, ladders)
        print(f"{s:>6d} → {label:11s} {pct:5.1f}%  rem={rem}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", choices=["junior","senior","both"], default="senior")
    ap.add_argument("--ladder", help="path to ladder.json (default: auto-find; prefers data/neuro-lite/ladder.json)")
    args = ap.parse_args()
    if args.domain == "both":
        main("junior", args.ladder); print("-"*60)
        main("senior", args.ladder)
    else:
        main(args.domain, args.ladder)
