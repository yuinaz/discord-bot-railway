# -*- coding: utf-8 -*-







import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))







COGS = os.path.join(ROOT, "satpambot", "bot", "modules", "discord_bot", "cogs")















DEFAULT_TARGETS = [







    "anti_url_phish_guard.py",







    "anti_url_phish_guard_bootstrap.py",







]















IMPORT_SNIP = "from satpambot.ml.guard_hooks import GuardAdvisor  # auto-injected"







PRECHECK_MARKER = "# auto-injected precheck (global thread exempt + whitelist)"























def revert_file(path: str) -> bool:







    try:







        with open(path, "r", encoding="utf-8") as f:







            txt = f.read()







    except FileNotFoundError:







        print("Not found:", os.path.basename(path))







        return False















    orig = txt







    txt = re.sub(







        r"\n\s*# auto-injected precheck.*?^\s*except\s+Exception:\s*\n\s*pass\s*\n",







        "\n",







        txt,







        flags=re.S | re.M,







    )







    txt = txt.replace(IMPORT_SNIP + "\n", "")







    txt = txt.replace(IMPORT_SNIP, "")















    if txt != orig:







        with open(path, "w", encoding="utf-8") as f:







            f.write(txt)







        print("Reverted:", os.path.basename(path))







        return True







    else:







        print("No changes:", os.path.basename(path))







        return False























def main():







    targets = sys.argv[1:] or DEFAULT_TARGETS







    changed = 0







    for name in targets:







        p = os.path.join(COGS, name)







        if revert_file(p):







            changed += 1







    print("Total reverted:", changed)







    return 0























if __name__ == "__main__":







    sys.exit(main())







