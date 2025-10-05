#!/usr/bin/env python3



"""



Inject compact assets into dashboard templates and remove stray templating artefacts.



- Adds <link ... layout_compact.css> after the theme css line if found, else before </head>.



- Adds <script ... compact_layout.js> before </body>.



- Cleans stray "' %}'" artefacts sometimes left by templating.



"""







import pathlib
import re
import sys

CSS_TAG = '<link rel="stylesheet" href="/dashboard/dashboard-static/css/layout_compact.css">'



JS_TAG = '<script src="/dashboard/dashboard-static/js/compact_layout.js"></script>'











def inject_file(path):



    s = pathlib.Path(path).read_text(encoding="utf-8")



    changed = False







    # remove stray templating artefact



    s2 = s.replace("' %}' '%}'", "").replace("'%}'", "").replace("' %}", "")



    if s2 != s:



        s = s2



        changed = True







    # insert CSS after theme if present



    if CSS_TAG not in s:



        s, n = re.subn(r"(<link[^>]+theme\.css[^>]*>)", r"\1\n  " + CSS_TAG, s, count=1, flags=re.I)



        if n == 0:



            s, n = re.subn(r"</head>", "  " + CSS_TAG + "\n</head>", s, count=1, flags=re.I)



        changed = changed or n > 0







    # insert JS before </body>



    if JS_TAG not in s:



        s, n = re.subn(r"</body>", JS_TAG + "\n</body>", s, count=1, flags=re.I)



        changed = changed or n > 0







    if changed:



        pathlib.Path(path).write_text(s, encoding="utf-8")



        print(f"[PATCH] updated: {path}")



    else:



        print(f"[PATCH] nochange: {path}")











def main():



    base = pathlib.Path(".")



    # Common template locations



    candidates = []



    for pat in [



        "satpambot/dashboard/templates/dashboard.html",



        "satpambot/dashboard/themes/gtake/templates/dashboard.html",



        "satpambot/dashboard/templates/base.html",



        "satpambot/dashboard/themes/gtake/templates/base.html",



    ]:



        p = base / pat



        if p.exists():



            candidates.append(str(p))



    # Also scan all dashboard templates as fallback



    for p in base.glob("satpambot/dashboard/**/templates/**/*.html"):



        candidates.append(str(p))







    seen = set()



    for path in candidates:



        if path in seen:



            continue



        seen.add(path)



        try:



            inject_file(path)



        except Exception as e:



            print(f"[PATCH] error {path}: {e}", file=sys.stderr)











if __name__ == "__main__":



    main()



