#!/usr/bin/env python3



from __future__ import annotations

import json
import pathlib

DATA = [



    ("data/phish_phash.json", {}),



]











def ensure(path, default):



    p = pathlib.Path(path)



    if not p.parent.exists():



        p.parent.mkdir(parents=True, exist_ok=True)



    if not p.exists():



        with open(p, "w", encoding="utf-8") as f:



            json.dump(default, f, indent=2, ensure_ascii=False)



        print("Created", p)



    else:



        print("OK", p)











if __name__ == "__main__":



    for path, default in DATA:



        ensure(path, default)



