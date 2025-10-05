#!/usr/bin/env python3



"""



Quick local check:



- Validates data/phish_phash.json and data/phish_lab/phash_blocklist.json



- Prints counts of valid 16-hex entries



"""







import json
import re
from pathlib import Path

HEX16 = re.compile(r"^[0-9a-f]{16}$", re.I)











def load_any(p: Path):



    try:



        return json.loads(p.read_text(encoding="utf-8"))



    except Exception:



        return None











def norm(obj):



    out = []







    def push(x):



        if isinstance(x, str) and HEX16.match(x.strip()):



            out.append(x.strip())







    if isinstance(obj, dict):



        if isinstance(obj.get("phash"), list):



            for h in obj["phash"]:



                push(h)



        if isinstance(obj.get("items"), list):



            for it in obj["items"]:



                if isinstance(it, dict):



                    push(it.get("hash"))



        if isinstance(obj.get("hashes"), list):



            for h in obj["hashes"]:



                push(h)



    elif isinstance(obj, list):



        for it in obj:



            if isinstance(it, dict):



                push(it.get("hash"))



            else:



                push(it)



    # unique



    seen = set()



    uniq = []



    for h in out:



        if h not in seen:



            seen.add(h)



            uniq.append(h)



    return uniq











def main():



    legacy = Path("data/phish_phash.json")



    newblk = Path("data/phish_lab/phash_blocklist.json")



    L = norm(load_any(legacy)) if legacy.exists() else []



    N = norm(load_any(newblk)) if newblk.exists() else []



    print(f"Legacy (data/phish_phash.json): {len(L)} valid entries")



    print(f"New    (data/phish_lab/phash_blocklist.json): {len(N)} valid entries")



    bad = []



    if legacy.exists():



        try:



            raw = json.loads(legacy.read_text(encoding="utf-8"))



            arr = raw.get("phash") if isinstance(raw, dict) else []



            for h in arr:



                if not (isinstance(h, str) and HEX16.match(h.strip())):



                    bad.append(h)



        except Exception:



            pass



    if bad:



        print(f"⚠ Found {len(bad)} invalid entries (not 16-hex pHash). Example: {bad[:3]}")



    else:



        print("✓ No invalid entries found in legacy file.")











if __name__ == "__main__":



    main()



