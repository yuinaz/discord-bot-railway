from __future__ import annotations

import os, io, zlib, json, sqlite3, time

def _db_path() -> str:
    return os.getenv("NEUROLITE_MEMORY_DB",
        os.path.join(os.path.dirname(__file__), "..","..","..","..","data","memory.sqlite3"))

def _open_db():
    path = _db_path()
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        try: os.makedirs(d, exist_ok=True)
        except Exception: pass
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con

def _ensure_tables(con: sqlite3.Connection):
    con.execute("""CREATE TABLE IF NOT EXISTS sticker_stats(
        emotion TEXT PRIMARY KEY,
        sent_count INTEGER DEFAULT 0,
        success_count INTEGER DEFAULT 0
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS slang_lexicon(
        token TEXT PRIMARY KEY,
        pos INTEGER DEFAULT 0,
        neg INTEGER DEFAULT 0,
        updated_ts INTEGER
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS progress_snapshots(
        day_ts INTEGER PRIMARY KEY,
        total_sent INTEGER,
        total_success INTEGER,
        lex_total INTEGER
    )""")
    con.commit()

def export_state(limit_tokens:int=800) -> bytes:
    con = _open_db()
    with con:
        _ensure_tables(con)
        stats = []
        for r in con.execute("SELECT emotion, sent_count, success_count FROM sticker_stats"):
            stats.append([r["emotion"], int(r["sent_count"] or 0), int(r["success_count"] or 0)])
        lex = []
        cur = con.execute("SELECT token,pos,neg,updated_ts,(pos+neg) AS score FROM slang_lexicon ORDER BY score DESC LIMIT ?", (int(limit_tokens),))
        for r in cur.fetchall():
            lex.append([r["token"], int(r["pos"] or 0), int(r["neg"] or 0), int(r["updated_ts"] or 0)])
        snaps = []
        cur = con.execute("SELECT day_ts,total_sent,total_success,lex_total FROM progress_snapshots ORDER BY day_ts DESC LIMIT 14")
        for r in cur.fetchall():
            snaps.append([int(r["day_ts"]), int(r["total_sent"]), int(r["total_success"]), int(r["lex_total"])])        
        obj = {"ts": int(time.time()), "sticker_stats": stats, "slang_lexicon": lex, "snapshots": snaps[::-1], "v": 1}
        raw = json.dumps(obj, separators=(",",":")).encode("utf-8")
        return zlib.compress(raw, level=6)

def import_state(data: bytes) -> dict:
    try:
        raw = zlib.decompress(data)
    except Exception:
        raw = data
    return json.loads(raw.decode("utf-8"))

def apply_state(obj: dict) -> None:
    con = _open_db()
    with con:
        _ensure_tables(con)
        for emo, sent, succ in obj.get("sticker_stats", []):
            con.execute("""INSERT INTO sticker_stats(emotion, sent_count, success_count)
                           VALUES (?,?,?)
                           ON CONFLICT(emotion) DO UPDATE SET
                            sent_count = MAX(sent_count, excluded.sent_count),
                            success_count = MAX(success_count, excluded.success_count)""",
                        (emo, int(sent), int(succ)))
        for token, pos, neg, uts in obj.get("slang_lexicon", []):
            con.execute("""INSERT INTO slang_lexicon(token,pos,neg,updated_ts)
                           VALUES (?,?,?,?)
                           ON CONFLICT(token) DO UPDATE SET
                            pos = MAX(pos, excluded.pos),
                            neg = MAX(neg, excluded.neg),
                            updated_ts = MAX(updated_ts, excluded.updated_ts)""",
                        (token, int(pos), int(neg), int(uts)))
        for day_ts, total_sent, total_success, lex_total in obj.get("snapshots", []):
            con.execute("""INSERT INTO progress_snapshots(day_ts,total_sent,total_success,lex_total)
                           VALUES (?,?,?,?)
                           ON CONFLICT(day_ts) DO UPDATE SET
                            total_sent = MAX(total_sent, excluded.total_sent),
                            total_success = MAX(total_success, excluded.total_success),
                            lex_total = MAX(lex_total, excluded.lex_total)""",
                        (int(day_ts), int(total_sent), int(total_success), int(lex_total)))
        con.commit()
