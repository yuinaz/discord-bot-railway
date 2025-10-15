# print_sanitizer.py
# Optional: if you import this file, it wraps builtins.print to avoid UnicodeEncodeError.
import builtins, sys

_orig_print = builtins.print
def _safe_print(*args, **kwargs):
    try:
        return _orig_print(*args, **kwargs)
    except UnicodeEncodeError:
        text = " ".join(str(a) for a in args)
        enc = (getattr(sys.stdout, "encoding", None) or "utf-8")
        try:
            data = text.encode(enc, errors="replace").decode(enc, errors="replace")
        except Exception:
            data = text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
        return _orig_print(data, **kwargs)

builtins.print = _safe_print
