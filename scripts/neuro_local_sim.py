#!/usr/bin/env python3
# (content trimmed for brevity in this comment; full content same as previous attempt)
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
from typing import Dict

BASE_DEFAULT = Path("data/neuro-lite")
LADDER_DEFAULT = BASE_DEFAULT / "ladder.json"

DEFAULT_LADDER = {
    "junior": {"TK": {"L1": 100, "L2": 150}},
    "senior": {"SD": {"L1": 150, "L2": 250, "L3": 400, "L4": 600, "L5": 800, "L6": 1000}},
}

def load_json(p: Path, default):
    if not p.exists():
        return json.loads(json.dumps(default))
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return json.loads(json.dumps(default))

def save_json(p: Path, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def split_levels(total_xp: int, stages: Dict[str, int]):
    out = {}
    rem = int(total_xp)
    for level_name, need in stages.items():
        need = max(1, int(need))
        if rem <= 0:
            out[level_name] = 0
        elif rem >= need:
            out[level_name] = 100
            rem -= need
        else:
            out[level_name] = int(round(100 * (rem / need)))
            rem = 0
    overall = int(round(sum(out.values()) / max(1, len(out))))
    return out, overall

def compute_progress(xp_j: int, xp_s: int, ladder):
    def build(xp, section):
        tree, ovs = {}, []
        for block, levels in ladder.get(section, {}).items():
            perc, ov = split_levels(xp, levels)
            tree[block] = perc
            ovs.append(ov)
        overall = int(round(sum(ovs) / max(1, len(ovs)))) if ovs else 0
        return tree, overall

    j_tree, j_overall = build(xp_j, "junior")
    s_tree, s_overall = build(xp_s, "senior")
    gate = {"promotion_allowed": bool(j_overall >= 100), "ts": int(time.time())}
    return ({"overall": j_overall, **j_tree},
            {"overall": s_overall, **s_tree},
            gate)

def main(argv=None):
    ap = argparse.ArgumentParser(description="Simulasi progres NEURO-LITE (offline)")
    ap.add_argument("--xp-j", type=int, default=0)
    ap.add_argument("--xp-s", type=int, default=0)
    ap.add_argument("--set", dest="set_mode", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--base", type=str, default=str(BASE_DEFAULT))
    ap.add_argument("--ladder", type=str, default=str(LADDER_DEFAULT))
    args = ap.parse_args(argv)

    base = Path(args.base); base.mkdir(parents=True, exist_ok=True)

    if args.reset:
        now = int(time.time())
        save_json(base/"bridge_junior.json", {"xp":0,"updated":now})
        save_json(base/"bridge_senior.json", {"xp":0,"updated":now})
        for name in ("learn_progress_junior.json","learn_progress_senior.json","gate_status.json"):
            try: (base/name).unlink()
            except FileNotFoundError: pass
        print("reset ok"); return 0

    ladder = load_json(Path(args.ladder), DEFAULT_LADDER)
    bj = load_json(base/"bridge_junior.json", {"xp":0,"updated":0})
    bs = load_json(base/"bridge_senior.json", {"xp":0,"updated":0})

    if args.set_mode:
        j_xp = max(0, int(args.xp_j)); s_xp = max(0, int(args.xp_s))
    else:
        j_xp = int(bj.get("xp",0)) + max(0, int(args.xp_j))
        s_xp = int(bs.get("xp",0)) + max(0, int(args.xp_s))

    lp_j, lp_s, gate = compute_progress(j_xp, s_xp, ladder)
    print(json.dumps({
        "bridge":{"junior_xp": j_xp, "senior_xp": s_xp},
        "learn_progress_junior": lp_j,
        "learn_progress_senior": lp_s,
        "gate_status": gate
    }, ensure_ascii=False, indent=2))

    if args.dry_run: return 0

    now = int(time.time())
    save_json(base/"bridge_junior.json", {"xp": j_xp, "updated": now})
    save_json(base/"bridge_senior.json", {"xp": s_xp, "updated": now})
    save_json(base/"learn_progress_junior.json", lp_j)
    save_json(base/"learn_progress_senior.json", lp_s)
    save_json(base/"gate_status.json", gate)
    print("files written."); return 0

if __name__ == "__main__":
    raise SystemExit(main())
