
"""
scripts_compile_satpambot_only.py
- Kompilasi hanya 'satpambot' (menghindari folder duplikat seperti 'bot/' & 'modules/')
"""
import compileall, sys
from pathlib import Path

root = Path(".").resolve()
satpam = root / "satpambot"
if not satpam.exists():
    print("[ERR] folder 'satpambot' tidak ditemukan:", satpam)
    sys.exit(2)

print("[INFO] compileall satpambot/...")
ok = compileall.compile_dir(str(satpam), maxlevels=20, quiet=1)
if not ok:
    print("[WARN] compileall melaporkan masalah")
    sys.exit(1)
print("[OK] compile satpambot sukses")
