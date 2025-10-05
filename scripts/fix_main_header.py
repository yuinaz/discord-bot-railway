import io
import re

P = "main.py"



s = io.open(P, "r", encoding="utf-8", errors="ignore").read()







# 1) buang blok-blok sisipan lama agar tidak dobel / setengah



s = re.sub(



    r"^[ \t]*# === (AUTO RUN_BOT|SILENCE /api/live) ===.*?^[ \t]*# === END ===\r?\n?",



    "",



    s,



    flags=re.S | re.M,



)



s = re.sub(r"^\s*load_dotenv\((?s).*?^\s*$", s, s, flags=re.M)  # (noop safeguard)



# hapus pemanggilan load_dotenv yang duplikat (biar kita taruh ulang)



s = re.sub(r"^\s*load_dotenv\([^\)]*\)\s*$", "", s, flags=re.M)



# hapus import dotenv duplikat, nanti kita inject ulang



s = re.sub(r"^\s*from dotenv import load_dotenv\s*$", "", s, flags=re.M)







# 2) siapkan header baru yang valid



HEADER = (



    """\



import os, logging



from dotenv import load_dotenv







# .env utama lalu .env.local override untuk lokal



load_dotenv()



load_dotenv('.env.local', override=True)







# === AUTO RUN_BOT based on token from .env/.env.local ===



try:



    token = None



    for key in ("DISCORD_TOKEN","DISCORD_BOT_TOKEN","BOT_TOKEN","TOKEN","TOKEN_BOT"):



        val = os.getenv(key)



        if val and val.strip():



            token = val.strip()



            os.environ["DISCORD_TOKEN"] = token  # normalisasi nama



            break



    run_bot = (os.getenv("RUN_BOT","auto").strip().lower())



    if token and run_bot in ("auto","","0","false","off"):



        os.environ["RUN_BOT"] = "1"



except Exception:



    pass



# === END ===







# === SILENCE /api/live ===



try:



    from werkzeug.serving import WSGIRequestHandler



    class _SilenceLive(logging.Filter):



        def filter(self, record):



            try:



                m = record.getMessage()



            except Exception:



                return True



            return "/api/live" not in m



    # filter di logger werkzeug



    for name in ("werkzeug","werkzeug.serving"):



        lg = logging.getLogger(name)



        lg.addFilter(_SilenceLive())



        for h in list(getattr(lg, "handlers", []) or []):



            try:



                h.addFilter(_SilenceLive())



            except Exception:



                pass



    # patch handler agar baris akses /api/live tidak tercetak



    _orig_log_request = WSGIRequestHandler.log_request



    def _log_request_sans_live(self, code='-', size='-'):



        line = getattr(self, "requestline", "") or ""



        if "/api/live" in line:



            return



        return _orig_log_request(self, code, size)



    WSGIRequestHandler.log_request = _log_request_sans_live



except Exception:



    pass



# === END ===



""".rstrip()



    + "\n"



)







# 3) sisipkan header di paling atas, tapi jaga agar tidak duplikasi import pertama



#    (kalau file sudah punya shebang/encoding comment, taruh setelahnya)



lines = s.splitlines(True)



insert_at = 0



if lines and lines[0].startswith("#!") or (lines and "coding" in lines[0]):



    insert_at = 1







new = HEADER + "".join(lines[insert_at:])



io.open(P, "w", encoding="utf-8", newline="\n").write(new)



print("OK: header main.py ditata ulang (env + auto run + silence live).")



