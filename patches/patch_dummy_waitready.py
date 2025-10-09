#!/usr/bin/env python3
"""
patches/patch_dummy_waitready.py

Tujuan:
- Tambahkan method async `wait_until_ready()` ke DummyBot di
  satpambot/bot/modules/discord_bot/helpers/smoke_utils.py
- Idempotent: jika sudah ada, tidak diubah.
- Tidak mengubah config / format file lain.

Cara pakai:
    python patches/patch_dummy_waitready.py [path_smoke_utils.py]

Jika argumen tidak diberikan, script akan mencoba path default:
    satpambot/bot/modules/discord_bot/helpers/smoke_utils.py
"""
import sys, re, os, io

DEFAULT_PATH = os.path.join("satpambot","bot","modules","discord_bot","helpers","smoke_utils.py")

PATCH_SNIPPET = """
    async def wait_until_ready(self):
        \"\"\"Dummy wait_until_ready untuk smoke test offline.
        Segera selesai; cukup kompatibel dengan cogs yang `await bot.wait_until_ready()`.
        \"\"\"
        return None
"""

def load_text(path):
    with io.open(path, "r", encoding="utf-8") as f:
        return f.read()

def save_text(path, text):
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)

def ensure_wait_until_ready_in_class(src):
    # Sudah ada?
    if re.search(r"^\s*async\s+def\s+wait_until_ready\s*\(", src, flags=re.M):
        return src, False

    # Cari definisi class DummyBot (top-level)
    cls_match = re.search(r"^class\s+DummyBot\b[^\n]*:\s*", src, flags=re.M)
    if not cls_match:
        raise SystemExit("Gagal: class DummyBot tidak ditemukan di smoke_utils.py")

    cls_start = cls_match.start()
    cls_header_end = cls_match.end()

    # Cari akhir blok class: next top-level class/def ATAU EOF
    next_top = re.search(r"^class\s+\w+\b|^def\s+\w+\b", src[cls_header_end:], flags=re.M)
    if next_top:
        cls_end = cls_header_end + next_top.start()
    else:
        cls_end = len(src)

    class_block = src[cls_header_end:cls_end]

    # Deteksi indent method di dalam class (default 4 spasi)
    m_ind = re.search(r"^([ \t]+)(?:async\s+def|def)\s+\w+\s*\(", class_block, flags=re.M)
    indent = m_ind.group(1) if m_ind else "    "

    snippet = "\n" + indent + "async def wait_until_ready(self):\n" \
              + indent + "    " + "return None\n"

    # Sisipkan menjelang akhir class
    patched = src[:cls_end].rstrip() + "\n" + snippet + "\n" + src[cls_end:]
    return patched, True

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    if not os.path.exists(path):
        raise SystemExit(f"File tidak ditemukan: {path}")

    src = load_text(path)
    try:
        new_src, changed = ensure_wait_until_ready_in_class(src)
    except Exception as e:
        raise

    if changed:
        # backup
        bak = path + ".bak"
        if not os.path.exists(bak):
            with open(bak, "wb") as f:
                f.write(src.encode("utf-8"))
        save_text(path, new_src)
        print(f"[ok] patched: {path}")
    else:
        print(f"[skip] sudah ada wait_until_ready(): {path}")

if __name__ == "__main__":
    main()
