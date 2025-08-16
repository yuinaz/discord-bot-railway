import io, re

p = "main.py"
s = io.open(p, "r", encoding="utf-8", errors="ignore").read()

# buang semua blok silencer lama
s = re.sub(r'^[ \t]*# === SILENCE /api/live ===.*?^[ \t]*# === END ===\r?\n?', '', s, flags=re.S|re.M)

block = """
# === SILENCE /api/live ===
try:
    import logging
    from werkzeug.serving import WSGIRequestHandler

    class _SilenceLive(logging.Filter):
        def filter(self, record):
            try:
                m = record.getMessage()
            except Exception:
                return True
            return "/api/live" not in m

    # pasang filter ke logger dan handlernya
    for name in ("werkzeug", "werkzeug.serving"):
        lg = logging.getLogger(name)
        if lg:
            lg.addFilter(_SilenceLive())
            for h in list(getattr(lg, "handlers", []) or []):
                try:
                    h.addFilter(_SilenceLive())
                except Exception:
                    pass

    # patch handler supaya baris akses /api/live tidak ditulis
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
""".strip("\n")

# cari baris run() untuk mengambil indent dan sisipkan tepat sebelum run()
m = re.search(r'^([ \t]*)(?:socketio|app)\.run\(', s, flags=re.M)
if m:
    indent = m.group(1)
    indented = "\n" + "\n".join((indent + ln if ln.strip() else ln) for ln in block.splitlines()) + "\n"
    s = s[:m.start()] + indented + s[m.start():]
else:
    # fallback: taruh di akhir file (tidak di dalam blok apa pun)
    s = s.rstrip() + "\n\n" + block + "\n"

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("OK: silencer replaced with proper indentation.")
