
import os, json, shutil, sys
from pathlib import Path

SRC_DIR = Path("config")                 # ROOT repo config
DST_DIR = Path("satpambot/config")       # runtime path

# presence config candidates (respect user's repo file names)
PRESENCE_FILES = [
    "presence_mood_rotator.json",
    "pressence_mood_rotator.json",  # typo variant commonly seen
]

def copy_jsons():
    if not SRC_DIR.exists():
        print(f"[INFO] {SRC_DIR} tidak ada — lewati bridge.")
        return 0
    DST_DIR.mkdir(parents=True, exist_ok=True)

    copied = 0
    # copy all jsons
    for j in SRC_DIR.glob("*.json"):
        # never copy 99_env_override.json out of root (should live in satpambot/config only)
        if j.name.lower() == "99_env_override.json":
            continue
        dst = DST_DIR / j.name
        shutil.copy2(j, dst)
        print(f"[SYNC] {j} -> {dst}")
        copied += 1

    # Make sure presence file exists if present on SRC (not required to run)
    found_presence = None
    for name in PRESENCE_FILES:
        src = SRC_DIR / name
        if src.exists():
            dst = DST_DIR / name
            if not dst.exists() or src.read_text(encoding="utf-8", errors="ignore") != dst.read_text(encoding="utf-8", errors="ignore"):
                shutil.copy2(src, dst)
                print(f"[SYNC] {src} -> {dst} (presence)")
            found_presence = name
            break

    if found_presence:
        print(f"[OK] Presence config ditemukan: {found_presence}")
    else:
        print("[WARN] Presence config tidak ditemukan di ROOT config/. Bot tetap jalan, tapi rotator bisa tidak aktif.")

    return copied

if __name__ == "__main__":
    n = copy_jsons()
    print(f"[DONE] Bridge selesai. {n} file tersalin.")
