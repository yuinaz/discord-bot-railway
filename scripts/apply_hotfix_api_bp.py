import argparse, sys, os, re, shutil
from pathlib import Path

EXCLUDES = {'.git', '.hg', '.svn', '.idea', '.vscode', '.mypy_cache', '__pycache__', 'venv', '.venv', 'env'}

def should_skip(path: Path) -> bool:
    parts = set(p.name for p in path.parents)
    if any(ex in parts for ex in EXCLUDES):
        return True
    return False

def main():
    ap = argparse.ArgumentParser(description="Hotfix: replace 'api_bp' -> 'api_bp' in .py files (config-safe)")
    ap.add_argument("--root", default=".", help="Repo root (default: current directory)")
    ap.add_argument("--dry-run", action="store_true", help="Only print what would change, do not modify files")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"[ERR] Root not found: {root}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Scanning under: {root}")
    changed = []
    for p in root.rglob("*.py"):
        if any(part in EXCLUDES for part in p.parts):
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            print(f"[WARN] Skip unreadable file: {p} ({e})")
            continue

        if "api_bp" in txt or "@api_bp." in txt:
            new_txt = txt.replace("@api_bp.", "@api_bp.").replace("api_bp", "api_bp")
            if new_txt != txt:
                rel = p.relative_to(root)
                if args.dry_run:
                    print(f"[DRY] Would patch: {rel}")
                    changed.append(str(rel))
                else:
                    bak = p.with_suffix(p.suffix + ".bak")
                    try:
                        shutil.copy2(p, bak)
                        p.write_text(new_txt, encoding="utf-8")
                        print(f"[OK ] Patched: {rel} (backup: {bak.name})")
                        changed.append(str(rel))
                    except Exception as e:
                        print(f"[ERR] Failed to patch {rel}: {e}")
    if not changed:
        print("[INFO] No files contained 'api_bp'. Nothing changed.")
    else:
        print(f"[INFO] Done. Files patched: {len(changed)}")

if __name__ == "__main__":
    main()