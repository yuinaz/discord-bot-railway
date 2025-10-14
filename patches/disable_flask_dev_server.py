# -*- coding: utf-8 -*-
<<<<<<< HEAD
=======
from __future__ import annotations
>>>>>>> ef940a8 (heal)







"""







patches/disable_flask_dev_server.py







-----------------------------------







- Menulis file: satpambot/dashboard/dev_server_guard.py







- Menyuntikkan import guard ke awal main.py (tanpa mengubah logika lain)







- Aman dijalankan berkali-kali (idempotent).







"""















<<<<<<< HEAD
from __future__ import annotations
=======
>>>>>>> ef940a8 (heal)

import os
from pathlib import Path

GUARD_PATH = Path("satpambot/dashboard/dev_server_guard.py")







MAIN_PATHS = [







    Path("main.py"),







    Path("entry.py"),







    Path("src/main.py"),







]















GUARD_SRC = '# -*- coding: utf-8 -*-\n"""\ndev_server_guard\n----------------\nMemonkeypatch Flask.dev server agar *tidak* bisa start di produksi.\nTujuan: cegah bentrok port ketika `main.py` sudah menjalankan web server (waitress/wsgi).\n\nAktif otomatis saat import. Tidak mengubah format config apa pun.\nUntuk lokal dev (ingin `app.run()`): export RUN_LOCAL_DEV=1.\n"""\nimport os\ntry:\n    from flask import Flask  # type: ignore\nexcept Exception:\n    Flask = None\n\nif Flask is not None and os.getenv("RUN_LOCAL_DEV") != "1":\n    _orig_run = Flask.run\n\n    def _guarded_run(self, *args, **kwargs):\n        import logging\n        logging.getLogger(__name__).info("[dev-server-guard] Suppressed Flask app.run(); main.py handles the server.")\n        # NO-OP in production\n        return\n\n    try:\n        Flask.run = _guarded_run  # type: ignore[attr-defined]\n    except Exception:\n        # Best-effort; kalau gagal monkeypatch, biarkan saja (tidak fatal)\n        pass\n'  # noqa: E501























def write_guard():







    GUARD_PATH.parent.mkdir(parents=True, exist_ok=True)







    GUARD_PATH.write_text(GUARD_SRC, encoding="utf-8", newline="\n")







    print(f"[OK] Wrote guard: {GUARD_PATH}")























def inject_import(p: Path) -> bool:







    if not p.exists():







        return False







    s = p.read_text(encoding="utf-8")







    if "satpambot.dashboard.dev_server_guard" in s:







        print(f"[SKIP] Import already present in {p}")







        return True















    # sisipkan sedini mungkin (setelah shebang/encoding/first docstring)







    lines = s.splitlines(True)







    insert_at = 0















    # skip shebang







    if insert_at < len(lines) and lines[insert_at].startswith("#!"):







        insert_at += 1







    # skip encoding cookie







    if insert_at < len(lines) and "coding" in lines[insert_at] and "utf-8" in lines[insert_at]:







        insert_at += 1







    # skip module docstring







    if insert_at < len(lines) and lines[insert_at].lstrip().startswith(('"""', "'''")):







        q = lines[insert_at].lstrip()[:3]







        insert_at += 1







        while insert_at < len(lines) and q not in lines[insert_at]:







            insert_at += 1







        if insert_at < len(lines):







            insert_at += 1















    stub = "import satpambot.dashboard.dev_server_guard  # noqa: F401  # stop Flask app.run() in prod\n"







    lines.insert(insert_at, stub)







    p.write_text("".join(lines), encoding="utf-8", newline="\n")







    print(f"[OK] Injected guard import into {p}")







    return True























def main():







    write_guard()







    injected_any = False







    for mp in MAIN_PATHS:







        injected_any |= inject_import(mp)







    if not injected_any:







        print("[WARN] main.py tidak ditemukan; silakan tambahkan import ini manual di entrypoint anda:")







        print("  import satpambot.dashboard.dev_server_guard  # noqa")







    print("[DONE] disable_flask_dev_server")























if __name__ == "__main__":







    main()






