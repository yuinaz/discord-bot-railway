
import os, sys, sqlite3, json, pathlib, importlib, runpy

def _guess_db_path():
    p = os.getenv("ENV_DB_PATH")
    if p: return p
    here = pathlib.Path(__file__).resolve()
    return str(here.parents[1] / "data" / "runtime_env.db")

def preload_env_from_db():
    path = _guess_db_path()
    try:
        con = sqlite3.connect(path)
        cur = con.execute("SELECT key, value FROM runtime_env")
        for k, v in cur.fetchall():
            os.environ.setdefault(str(k), str(v))
    except Exception:
        pass
    finally:
        try: con.close()
        except Exception: pass

def main():
    preload_env_from_db()
    # default to main entry
    entry = os.getenv("ENTRY", "main")
    if entry.endswith(".py"):
        runpy.run_path(entry, run_name="__main__")
    else:
        runpy.run_module(entry, run_name="__main__")

if __name__ == "__main__":
    main()
