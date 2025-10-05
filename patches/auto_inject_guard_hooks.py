# -*- coding: utf-8 -*-







import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))







COGS = os.path.join(ROOT, "satpambot", "bot", "modules", "discord_bot", "cogs")















# Avoid injecting into URL-only guards







EXCLUDE_BASENAMES = {







    "anti_url_phish_guard.py",







    "anti_url_phish_guard_bootstrap.py",







}















IMPORT_SNIP = "from satpambot.ml.guard_hooks import GuardAdvisor  # auto-injected"







PRECHECK_SNIP = (







    "        # auto-injected precheck (global thread exempt + whitelist)\n"







    "        try:\n"







    "            _gadv = getattr(self, '_guard_advisor', None)\n"







    "            if _gadv is None:\n"







    "                self._guard_advisor = GuardAdvisor(self.bot)\n"







    "                _gadv = self._guard_advisor\n"







    "            from inspect import iscoroutinefunction\n"







    "            if _gadv.is_exempt(message):\n"







    "                return\n"







    "            if iscoroutinefunction(_gadv.any_image_whitelisted_async):\n"







    "                if await _gadv.any_image_whitelisted_async(message):\n"







    "                    return\n"







    "        except Exception:\n"







    "            pass\n"







)























def looks_like_image_guard(path: str, text: str) -> bool:







    name = os.path.basename(path).lower()







    if any(k in name for k in ["image", "phash", "attach", "ocr", "phish_hash"]):







        return True







    if re.search(r"(attachments|image/|pHash|dhash|PIL|content_type)", text, re.I):







        return True







    return False























def already_injected(text: str) -> bool:







    return "auto-injected precheck" in text























def inject_into_on_message(text: str):







    pat = re.compile(







        r"async\s+def\s+on_message\s*\(\s*self\s*,\s*message\s*:\s*discord\.Message\s*\)\s*:\s*\n",







        re.I,







    )







    m = pat.search(text)







    if not m:







        return None







    insert_at = m.end()







    return text[:insert_at] + PRECHECK_SNIP + text[insert_at:]























def ensure_import(text: str) -> str:







    if IMPORT_SNIP in text:







        return text







    lines = text.splitlines(True)







    for i, ln in enumerate(lines[:80]):







        if ln.startswith("from discord") or ln.startswith("import discord"):







            lines.insert(i + 1, IMPORT_SNIP + "\n")







            return "".join(lines)







    return IMPORT_SNIP + "\n" + text























def main():







    if not os.path.isdir(COGS):







        print("COGS folder tidak ditemukan:", COGS)







        return 0







    changed = 0







    for fn in os.listdir(COGS):







        if not fn.endswith(".py"):







            continue







        if fn in EXCLUDE_BASENAMES:







            print("Skip (excluded):", fn)







            continue







        path = os.path.join(COGS, fn)







        try:







            with open(path, "r", encoding="utf-8") as f:







                txt = f.read()







        except Exception:







            continue







        if not looks_like_image_guard(path, txt):







            print("Skip (non-image guard):", fn)







            continue







        if already_injected(txt):







            print("Skip (already injected):", fn)







            continue







        inj = inject_into_on_message(txt)







        if inj is None:







            print("Skip (no async on_message):", fn)







            continue







        inj = ensure_import(inj)







        with open(path, "w", encoding="utf-8") as f:







            f.write(inj)







        changed += 1







        print("Injected:", fn)







    print(f"Done. Files injected: {changed}")







    return 0























if __name__ == "__main__":







    sys.exit(main())







