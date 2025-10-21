#!/usr/bin/env python3
import os, json, argparse
import httpx

SENIOR_PHASES = ["SMP", "SMA", "KULIAH"]

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

def _load_ladders_from_repo():
    cur = os.path.abspath(os.path.dirname(__file__))
    for _ in range(10):
        cand = os.path.join(cur, "..","data","neuro-lite","ladder.json")
        cand = os.path.abspath(cand)
        if os.path.exists(cand):
            with open(cand, "r", encoding="utf-8") as f:
                j = json.load(f)
            ladders = {}
            for domain in ("junior","senior"):
                d = j.get(domain) or {}
                for phase, stages in d.items():
                    ladders[phase] = {str(k): int(v) for k,v in stages.items()}
            return ladders
        cur = os.path.dirname(cur)
    return {}

def _compute_label(total, ladders):
    spent = 0
    def ordered_items(dct):
        return sorted(list(dct.items()), key=lambda kv: _parse_stage_key(kv[0]))
    for phase in SENIOR_PHASES:
        chunks = ladders.get(phase, {})
        for (stage, need) in ordered_items(chunks):
            need = max(1, int(need))
            have = max(0, total - spent)
            if have < need:
                pct = 100.0 * (have / float(need))
                rem = max(0, need - have)
                return (f"{phase}-S{_parse_stage_key(stage)}", round(pct,1), rem)
            spent += need
    last = SENIOR_PHASES[-1]
    last_idx = len(ordered_items(ladders.get(last, {"S1":1})))
    return (f"{last}-S{last_idx}", 100.0, 0)

def main(args):
    base = os.getenv("UPSTASH_REDIS_REST_URL","").rstrip("/")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN","")
    if not base or not token:
        print("Upstash env missing.")
        return 1
    xp_key = args.xp_key or os.getenv("XP_SENIOR_KEY","xp:bot:senior_total")
    headers = {"Authorization": f"Bearer {token}", "Content-Type":"application/json"}
    ladders = _load_ladders_from_repo()
    with httpx.Client(timeout=15.0) as http:
        def get_key(k):
            try:
                r = http.get(f"{base}/get/{k}", headers=headers)
                r.raise_for_status()
                return r.json().get("result")
            except Exception:
                return None
        def mset_pipeline(kv):
            try:
                commands = [["SET", k, v] for k, v in kv.items()]
                r = http.post(f"{base}/pipeline", headers=headers, json=commands)
                r.raise_for_status()
                return True
            except Exception:
                return False

        raw = get_key(xp_key)
        print(f"[diag] UPSTASH_REDIS_REST_URL = {base}")
        print(f"[diag] XP_SENIOR_KEY          = {xp_key}")
        print(f"[diag] raw XP value           = {raw!r}")

        try_total = 0
        try:
            try_total = int(raw) if raw is not None else 0
        except Exception:
            try:
                j = json.loads(raw)
                try_total = int(j.get("overall",0))
            except Exception:
                try_total = 0

        label, pct, rem = _compute_label(try_total, ladders)
        live_raw = get_key("learning:status_json")
        live_label = None
        if live_raw:
            try: live_label = json.loads(live_raw).get("label")
            except Exception: live_label = None
        env_floor = os.getenv("LEARNING_MIN_LABEL","").strip() or None
        def R(l): 
            if not l: return (-1,0)
            p,s=(l.split("-",1)+["S0"])[:2]
            tab={"SMP":0,"SMA":1,"KULIAH":2}
            try: return (tab.get(p,-1), int(s.upper().replace("S","")))
            except Exception: return (tab.get(p,-1),0)
        floor = env_floor or live_label
        if floor and R(label) < R(floor):
            label = floor

        phase = label.split("-")[0]
        status = f"{label} ({pct:.1f}%)"
        status_json = json.dumps({"label":label,"percent":pct,"remaining":rem,"senior_total":try_total}, separators=(",",":"))
        print("Computed:", status_json)
        if args.write:
            ok = mset_pipeline({
                "learning:status": status,
                "learning:status_json": status_json,
                "learning:phase": phase
            })
            print("Wrote (pipeline):", ok)
    return 0

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--xp-key", help="Upstash key to read senior XP from (overrides env XP_SENIOR_KEY)")
    args = ap.parse_args()
    raise SystemExit(main(args))
