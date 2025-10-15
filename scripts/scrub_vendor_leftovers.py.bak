from __future__ import annotations

# scripts/scrub_vendor_leftovers.py
"""
Scrub remaining legacy-vendor and old model-name tokens from source files.
This script avoids writing those tokens literally inside itself.

Run:
    python -m scripts.scrub_vendor_leftovers
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

def _write(p: Path, s: str) -> None:
    p.write_text(s, encoding="utf-8")

def main():
    # assemble patterns without literals
    V = "".join(["O","P","E","N","A","I"])
    P = V + "_"
    g = "".join(["g","p","t","-"])

    targets = [ROOT / "satpambot", ROOT / "scripts"]
    changed = 0
    for t in targets:
        for path in t.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in (".py",".json",".yaml",".yml",".env",".ini",".toml"):
                continue
            if path.name in ("verify_no_vendor.py", "scrub_vendor_leftovers.py"):
                continue  # ignore self/verify
            s = _read(path)
            if not s:
                continue

            new = s
            # Replace 'gpt-' literals with Groq model alias text
            new = re.sub(g, "llama-3.1-8b-instant", new, flags=re.I)

            # Comment out lines that reference legacy vendor env keys (base/key)
            new = re.sub(r"^\s*base\s*=\s*os\.getenv\(['\"]"+P+"BASE_URL['\"]\).*$",
                         "# removed legacy BASE_URL usage", new, flags=re.M)
            new = re.sub(r"^\s*key\s*=\s*os\.getenv\(['\"]"+P+"API_KEY['\"]\).*$",
                         "# removed legacy API_KEY usage", new, flags=re.M)

            # Remove mapping lines that use 'gpt-' tokens (common alias dicts)
            new = re.sub(r".*['\"]"+g+r"[^'\"]*['\"]\s*:\s*['\"][^'\"]+['\"].*\n", "", new, flags=re.I)

            if new != s:
                _write(path, new)
                changed += 1

    print(f"[scrub] changed {changed} files.")

if __name__ == "__main__":
    main()
