import re
import sys

p = r"satpambot/dashboard/app.py"



s = open(p, "r", encoding="utf-8").read()



pat = re.compile(r"# === PATCH START: dashboard templates/routing ===.*?# === PATCH END ===", re.S)



blocks = list(pat.finditer(s))



if len(blocks) <= 1:



    print("nothing to dedupe")



    sys.exit(0)



keep = blocks[0]



out = s[: keep.end()]



last = keep.end()



for b in blocks[1:]:



    # simpan teks di antara blok-blok duplikat, lalu SKIP isi blok duplikat



    out += s[last : b.start()]



    last = b.end()



out += s[last:]



open(p, "w", encoding="utf-8", newline="\n").write(out)



print(f"Removed {len(blocks) - 1} duplicate block(s)")



