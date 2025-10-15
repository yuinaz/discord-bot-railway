import re, io

path = "main.py"
src = io.open(path, "r", encoding="utf-8", errors="ignore").read()

# hapus semua silencer lama (jika ada)
src = re.sub(r'^[ \t]*# === SILENCE /api/live ===.*?^[ \t]*# === END ===\r?\n?',
             '', src, flags=re.S|re.M)

# cari baris run() untuk ambil indent
m = re.search(r'^([ \t]*)(?:socketio|app)\.run\(', src, flags=re.M)
indent = m.group(1) if m else ''

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
    logging.getLogger("werkzeug").addFilter(_SilenceLive())
    _orig_log_request = WSGIRequestHandler.log_request
    def _log_request_sans_live(self, code='-', size='-'):
        p = getattr(self, 'path', '')
        if p.startswith("/api/live"):
            return
        return _orig_log_request(self, code, size)
    WSGIRequestHandler.log_request = _log_request_sans_live
except Exception:
    pass
# === END ===
""".strip("\n")

# terapkan indent jika disisipkan sebelum run() (di dalam block)
indented = "\n" + "\n".join((indent + ln if ln.strip() else ln) for ln in block.splitlines()) + "\n"

if m:
    i = m.start()
    out = src[:i] + indented + src[i:]
else:
    out = src.rstrip() + "\n\n" + block + "\n"

io.open(path, "w", encoding="utf-8", newline="\n").write(out)
print("Silencer reinserted with proper indentation.")
