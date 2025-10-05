#!/usr/bin/env python3


# scripts/import_phash_txt.py



import argparse, sys, json, re
from pathlib import Path

DEFAULT_TXT = Path("satpambot/dashboard/data/blacklist_image_hashes.txt")
DASHBOARD_JSON = Path("satpambot/dashboard/data/phash_index.json")
BOT_JSON = Path("data/phish_phash.json")  # default used by anti_image_phish_guard via PHISH_IMG_DB

HEX_RE = re.compile(r"[0-9a-fA-F]{6,64}")  # long-ish hex tokens

def parse_lines(text: str):
    vals = []
    for line in text.splitlines():
        for tok in HEX_RE.findall(line):
            vals.append(tok.lower())
    # unique, preserve order
    seen = set()
    out = []
    for h in vals:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out

def write_json(path: Path, hashes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump({"phash": list(hashes)}, f, ensure_ascii=False, indent=2)

def main():
    ap = argparse.ArgumentParser(description="Convert 'image hash.txt' -> JSON for dashboard and bot")
    ap.add_argument("txt", nargs="?", default=str(DEFAULT_TXT), help="Path to image hash txt (default: %(default)s)")
    ap.add_argument("--dashboard-json", default=str(DASHBOARD_JSON), help="Output JSON for dashboard API (default: %(default)s)")
    ap.add_argument("--bot-json", default=str(BOT_JSON), help="Output JSON for bot guard (default: %(default)s)")
    args = ap.parse_args()

    txt_path = Path(args.txt)
    if not txt_path.exists():
        print(f"[ERR] input file not found: {txt_path}", file=sys.stderr)
        sys.exit(2)

    hashes = parse_lines(txt_path.read_text(encoding="utf-8", errors="ignore"))
    write_json(Path(args.dashboard_json), hashes)
    write_json(Path(args.bot_json), hashes)

    print(f"[OK] parsed {len(hashes)} hashes")
    print(f"[OK] wrote dashboard JSON -> {args.dashboard_json}")
    print(f"[OK] wrote bot JSON       -> {args.bot_json}")
    print("\nNext steps:")
    print(" - Hit GET /api/phish/phash to verify the dashboard returns the list.")
    print(" - Bot guard will auto-reload within 60s (or restart bot to reload immediately).")

if __name__ == '__main__':
    main()
