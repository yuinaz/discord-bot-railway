# Satpambot Path Fix Patch (ModuleNotFoundError: No module named 'satpambot')

Masalahnya:
Saat menjalankan:
```
python scripts/smoke_deep.py
```
Python cuma menambahkan folder **scripts/** ke `sys.path`, bukan root project.
Akibatnya package top-level `satpambot/` tidak ketemu →
`ModuleNotFoundError: No module named 'satpambot'`.

Tiga cara perbaikan (pilih satu saja):

**Opsi A — Paling simpel (runner):**
1. Jalankan:
   ```
   python scripts/smoke_deep_runner.py
   ```
   Runner ini menambahkan root project ke `sys.path`, lalu menjalankan `smoke_deep.py` milikmu apa adanya.
   Tidak perlu mengubah file lama.

**Opsi B — Run as module (butuh __init__.py):**
1. Setelah patch ini diekstrak, folder `scripts/` sudah ada `__init__.py` (jadi package).
2. Jalankan dari root project:
   ```
   python -m scripts.smoke_deep
   ```

**Opsi C — Tambah 5 baris di awal file:**
1. Buka `scripts/smoke_deep.py`
2. Paste 5 baris di file `scripts/smoke_deep_INSERTPATH.patch.txt` tepat di paling atas file.
   (Di atas semua import lain.)
3. Simpan, lalu jalankan lagi:
   ```
   python scripts/smoke_deep.py
   ```

---

## Perintah cepat sesuai shell (Windows)

**CMD:**
```bat
set PYTHONPATH=%cd%
python scripts\smoke_deep.py
```

**PowerShell:**
```powershell
$env:PYTHONPATH = (Get-Location).Path
python scripts\smoke_deep.py
```

**Git Bash / MSYS2 / MINGW64:**
```bash
export PYTHONPATH="$(pwd)"
python scripts/smoke_deep.py
```

Opsi di atas adalah alternatif instan kalau belum ingin mengubah file sama sekali.
Tapi untuk jangka panjang, pakai **Opsi A** atau **Opsi B** supaya lebih stabil.

---

## Catatan tambahan (warning "coroutine was never awaited")
Jika nanti terlihat peringatan seperti:
`RuntimeWarning: coroutine 'XYZ.cog_load' was never awaited`,
itu karena smoke harness memanggil method async tanpa `await`.
Saya siapkan patch terpisah jika ingin: tinggal panggil loader yang
mendeteksi coroutine dan melakukan `await` hanya bila perlu.
(Bisa saya kirim menyusul kalau mau.)
