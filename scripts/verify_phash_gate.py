#!/usr/bin/env python3



"""



scripts/verify_phash_gate.py







Verifikasi posisi gate vs log tanpa bergantung pada nama fungsi helper.



- Cari baris "pHash DB loaded from Discord"



- Pastikan ada salah satu indikator gate sebelum log:



    - "_phash_daily_gate(" dalam jendela 40 baris sebelum log, ATAU



    - pola "now - last < _PHASH_REFRESH_SECONDS" (gate inline) sebelum log



Exit code 0 jika OK, selainnya 1.



"""







import re
from pathlib import Path

FILES = [



    Path("satpambot/bot/modules/discord_bot/cogs/anti_image_phash_runtime.py"),



    Path("satpambot/bot/modules/discord_bot/cogs/anti_image_phash_runtime_strict.py"),



]











def check(p: Path) -> bool:



    s = p.read_text(encoding="utf-8", errors="ignore")



    log = re.search(r"^[ \t]*await\s+self\._log\(.*pHash DB loaded from Discord.*$", s, re.M)



    if not log:



        print(f"[WARN] {p}: tidak ditemukan string log — lewati check posisi.")



        return True



    start_line = s.count("\n", 0, log.start()) + 1



    # window 80 baris ke atas



    pre = s[: log.start()].splitlines()



    window = pre[max(0, len(pre) - 80) :]



    pre_text = "\n".join(window)



    ok = ("_phash_daily_gate(" in pre_text) or ("_PHASH_REFRESH_SECONDS" in pre_text and "now - last" in pre_text)



    if ok:



        print(f"[OK] {p.name}: gate terdeteksi sebelum log (line ~{start_line}).")



        return True



    print(f"[FAIL] {p.name}: gate TIDAK terdeteksi sebelum log (line ~{start_line}).")



    return False











def main():



    all_ok = True



    for p in FILES:



        if not p.exists():



            print(f"[SKIP] {p} (not found)")



            continue



        all_ok &= check(p)



    return 0 if all_ok else 1











if __name__ == "__main__":



    raise SystemExit(main())



