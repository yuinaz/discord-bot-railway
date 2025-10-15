#!/usr/bin/env python3
# Merge multiple JSON patch files into local.json/satpambot_config.local.json (last wins).
# Tolerant to comments and trailing commas.

import json, re, sys, os
from pathlib import Path

BASE = "satpambot_config.local.json" if os.path.exists("satpambot_config.local.json") else "local.json"

def tload(txt):
    s = re.sub(r"//.*?$","",txt,flags=re.M)
    s = re.sub(r"/\*.*?\*/","",s,flags=re.S)
    s = re.sub(r",\s*([}\]])", r"\1", s)
    return json.loads(s)

def load_file(p):
    with open(p,"r",encoding="utf-8") as f:
        return tload(f.read())

def save_file(p,obj):
    with open(p,"w",encoding="utf-8") as f:
        json.dump(obj,f,indent=2,ensure_ascii=False)

def dmerge(dst,src):
    for k,v in src.items():
        if isinstance(v,dict) and isinstance(dst.get(k),dict):
            dmerge(dst[k],v)
        else:
            dst[k]=v
    return dst

def main(argv):
    if len(argv)<2:
        print("Usage: python -m scripts.merge_local_json_multi <file1.json> <file2.json> ...")
        sys.exit(2)
    base = load_file(BASE) if Path(BASE).exists() else {}
    for p in argv[1:]:
        part = load_file(p)
        dmerge(base, part)
        print(f"[merge] <- {p}")
    save_file(BASE, base)
    print(f"[merge] -> {BASE}")

if __name__=="__main__":
    main(sys.argv)
