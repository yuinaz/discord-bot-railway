from __future__ import annotations

import os
import sys
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]



if str(ROOT) not in sys.path:



    sys.path.insert(0, str(ROOT))







os.environ.setdefault("DISABLE_BOT_RUN", "1")











def _create_app():



    try:



        import app as appmod







        if hasattr(appmod, "create_app"):



            return appmod.create_app()



        if hasattr(appmod, "app"):



            return appmod.app



    except Exception as e:



        print("[warn] gagal import app:", e)



    # Fallback: build Flask and register UI



    from flask import Flask

    from satpambot.dashboard.merged_endpoints import register_merged_endpoints
    from satpambot.dashboard.webui import register_webui_builtin







    a = Flask("satpambot_dashboard")



    register_webui_builtin(a)



    try:



        register_merged_endpoints(a)



    except Exception:



        pass



    return a











app = _create_app()



c = app.test_client()











def expect(method, path, code=200, **kw):



    r = c.open(path, method=method, **kw)



    ok_codes = {code} if isinstance(code, int) else set(code)



    assert r.status_code in ok_codes, f"{method} {path} -> {r.status_code}"



    print("OK", method, path, "=>", r.status_code)



    return r











with c.session_transaction() as s:



    s["logged_in"] = True







expect("GET", "/dashboard", 200)



expect("GET", "/dashboard/settings", 200)



expect("GET", "/dashboard/security", 200)







expect("GET", "/dashboard/api/metrics", 200)



expect("GET", "/dashboard/api/banned_users", 200)











data = {"file": (BytesIO(b"fake"), "fake.png")}



expect(



    "POST",



    "/dashboard/api/phash/upload",



    code=(200,),



    data=data,



    content_type="multipart/form-data",



)



print("All smoketests PASSED")



