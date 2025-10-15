"""
Merge local JSON config with a template JSON.
Usage:
  python -m scripts.merge_local_json path/to/template.json  [path/to/target.json (default: satpambot_config.local.json)]
"""
import sys, json, os, pathlib

def deep_merge(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            out[k] = deep_merge(out[k], v) if k in out else v
        return out
    return b

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    tpl_path = sys.argv[1]
    target = sys.argv[2] if len(sys.argv) > 2 else "satpambot_config.local.json"
    with open(tpl_path, "r", encoding="utf-8") as f:
        tpl = json.load(f)
    if os.path.exists(target):
        with open(target, "r", encoding="utf-8") as f:
            try:
                cur = json.load(f)
            except Exception:
                cur = {}
    else:
        cur = {}
    merged = deep_merge(cur, tpl)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"[merge_local_json] merged -> {target}")

if __name__ == "__main__":
    main()
