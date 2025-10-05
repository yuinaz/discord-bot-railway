import io
import re

P = "main.py"



s = io.open(P, "r", encoding="utf-8", errors="ignore").read()







# --- bersihkan sisipan lama yang bikin SyntaxError ---



s = re.sub(r"^[ \t]*# === AUTO RUN_BOT.*?^[ \t]*# === END AUTO ===\r?\n?", "", s, flags=re.S | re.M)







# --- pastikan import dotenv ada ---



if "from dotenv import load_dotenv" not in s:



    # sisipkan setelah import os kalau ada, kalau tidak taruh di header



    m = re.search(r"^(import os.*\n)", s, flags=re.M)



    ins = "from dotenv import load_dotenv\n"



    if m:



        s = s[: m.end()] + ins + s[m.end() :]



    else:



        s = ins + s







# --- pastikan load_dotenv() ada (top-level) ---



if re.search(r"^\s*load_dotenv\(\)", s, flags=re.M) is None:



    # sisipkan setelah import dotenv



    m = re.search(r"^from dotenv import load_dotenv.*\n", s, flags=re.M)



    line = "load_dotenv()\n"



    s = (s[: m.end()] + line + s[m.end() :]) if m else (line + s)







# --- pastikan load .env.local override ---



if "load_dotenv('.env.local', override=True)" not in s and 'load_dotenv(".env.local", override=True)' not in s:



    m = re.search(r"^\s*load_dotenv\(\)\s*$", s, flags=re.M)



    line = "load_dotenv('.env.local', override=True)\n"



    s = (s[: m.end()] + line + s[m.end() :]) if m else (line + s)







# --- sisipkan blok AUTO RUN_BOT (top-level, bukan di dalam if) tepat setelah baris .env.local ---



auto = """



# === AUTO RUN_BOT based on token from .env/.env.local ===



try:



    import os



    token = None



    for key in ("DISCORD_TOKEN","DISCORD_BOT_TOKEN","BOT_TOKEN","TOKEN","TOKEN_BOT"):



        val = os.getenv(key)



        if val and val.strip():



            token = val.strip()



            os.environ["DISCORD_TOKEN"] = token  # normalize



            break



    run_bot = (os.getenv("RUN_BOT","auto").strip().lower())



    if token and run_bot in ("auto","","0","false","off"):



        os.environ["RUN_BOT"] = "1"



except Exception:



    pass



# === END AUTO ===



""".lstrip("\n")







# taruh setelah .env.local



m = re.search(r'^\s*load_dotenv\((?:\'|")\.env\.local(?:\'|"),\s*override=True\)\s*$', s, flags=re.M)



if m:



    s = s[: m.end()] + "\n" + auto + s[m.end() :]



else:



    # fallback: taruh setelah load_dotenv() pertama



    m2 = re.search(r"^\s*load_dotenv\(\)\s*$", s, flags=re.M)



    s = s[: m2.end()] + "\n" + auto + s[m2.end() :] if m2 else (auto + s)







io.open(P, "w", encoding="utf-8", newline="\n").write(s)



print("OK: main.py fixed for .env.local + RUN_BOT auto")



