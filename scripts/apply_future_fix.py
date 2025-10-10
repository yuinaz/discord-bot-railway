# Usage:
#   python scripts/apply_future_fix.py satpambot/ml/state_store_discord.py
# If no path given, it will patch that default file.
import sys, re, io, os

DEFAULT = os.path.join("satpambot", "ml", "state_store_discord.py")

def move_future_annotations(path: str) -> bool:
    with open(path, "r", encoding="utf-8") as fh:
        src = fh.read()

    # Remove any existing future annotations import
    pattern = r'^\s*from\s+__future__\s+import\s+annotations\s*\n'
    src_wo = re.sub(pattern, "", src, flags=re.MULTILINE)

    # Find module docstring (triple-quoted string at very top) to preserve order
    docstring_match = re.match(r'\s*(?:[urUR]?[\'"][\'"].*?[\'"][\'"]\s*)?', src_wo, flags=re.DOTALL)
    insert_pos = docstring_match.end() if docstring_match else 0

    new_src = src_wo[:insert_pos] + 'from __future__ import annotations\n' + src_wo[insert_pos:]

    if new_src == src:
        return False

    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new_src)
    return True

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    if not os.path.exists(path):
        print("File not found:", path, file=sys.stderr)
        sys.exit(2)
    changed = move_future_annotations(path)
    print("Patched" if changed else "No change needed", path)

if __name__ == "__main__":
    main()
