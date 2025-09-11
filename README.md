# SatpamBot — Discord Anti‑Phishing Guard (Free‑plan friendly)

**SatpamBot** adalah bot Discord + dashboard ringan untuk **menangkal phishing berbasis gambar & tautan**.  
Fokusnya: **stabil 24/7 di Render Free plan**, minim bandwidth, tanpa memaksa konfigurasi via *environment variables*.

---

## Fitur Utama

- 🛡️ **Deteksi gambar mirip (approximate)**: kombinasi **pHash ≈**, **dHash ≈**, dan **Tile pHash** (per‑bagian).  
  Kuat untuk variasi **format, crop, sudut, terang/gelap**. ORB (OpenCV) tersedia **opsional**.
- 🧠 **Auto reseed**: saat startup, bot otomatis **scan thread** `imagephising` dan membangun/menyatu‑kan DB hash di pesan `SATPAMBOT_PHASH_DB_V1` (parent channel).
- 🔁 **Runtime autoload**: daftar hash (pHash/dHash/tile) otomatis dimuat ke memori **saat bot siap** dan **setiap kali pesan DB di‑edit**.
- 💬 **Log ringkas**: ringkasan update dikirim ke parent channel & **auto‑delete** sesuai TTL (hemat noise).
- 📊 **Dashboard mini**: `/dashboard` dengan aset statis dan endpoint kesehatan:
  - `HEAD /healthz` – health check
  - `HEAD /uptime` – uptime probe
  - `GET  /botlive` – status bot (JSON)
  - `GET  /api/live/stats` – metrik ringan (guilds, online, latency, dll)
  - `GET  /api/phish/phash` – ringkasan hash **yang sedang dimuat di runtime**
- 🧪 **Smoke tests**: `scripts/smoketest_all.py` dan `scripts/smoke_cogs.py` untuk verifikasi cepat sebelum deploy.

---

## Arsitektur Singkat

```
satpambot/
  bot/modules/discord_bot/
    cogs/
      anti_image_phash_runtime.py     # deteksi runtime (pHash + dHash + tile) + autoload DB
      phish_hash_inbox.py             # daftar hash dari thread 'imagephising' → gabung ke DB message
      phish_hash_autoreseed.py        # sekali saat startup: scan & seed awal
      ... (cogs lain: link/url guard, metrics, dll)
    helpers/
      img_hashing.py                  # util pHash/dHash/tile (+ ORB opsional)
      static_cfg.py                   # semua toggle/threshold di sini (no ENV diperlukan)
app.py                                 # web app (uptime/health/dashboard)
main.py                                # entrypoint: jalankan web + bot
```

**DB hash** disimpan sebagai **pesan teks** oleh bot di parent channel bernama **`SATPAMBOT_PHASH_DB_V1`** berisi JSON code‑block:
```json
{
  "phash": ["...","..."],
  "dhash": ["...","..."],
  "tphash": ["...","..."]
}
```

> Runtime akan **autoload** daftar ini saat startup & setiap kali pesan di‑edit.

---

## Konfigurasi (tanpa ENV)

Semua toggle/threshold ada di `satpambot/bot/modules/discord_bot/helpers/static_cfg.py`.

Rekomendasi **Free plan** (aman & cukup ketat):
```python
# Approx thresholds
PHASH_HIT_DISTANCE = 15
DHASH_HIT_DISTANCE  = 17

# Tile pHash
TILE_GRID = 3
TILE_HIT_MIN = 6
TILE_PHASH_DISTANCE = 9

# Reseed & logging
PHISH_INBOX_THREAD = "imagephising"   # nama thread sumber contoh
PHISH_AUTO_RESEED_LIMIT = 2000        # jumlah pesan yang di-scan saat startup
PHISH_LOG_TTL = 30                    # auto-delete ringkasan log (detik)
PHISH_NOTIFY_THREAD = False           # agar ringkasan tidak spam di thread

# ORB (opsional, memakan CPU; set False untuk Free plan)
ORB_ENABLE = False
```

> **Token/credential**: repo ini **tidak** menyertakan rahasia. Cara pemberian token (ENV atau file privat) disesuaikan praktik Anda sendiri. **Jangan commit rahasia ke publik.**

---

## Menjalankan Lokal

Prasyarat: Python 3.10+

```bash
python -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Cek
python scripts/smoke_cogs.py
python scripts/smoketest_all.py

# Jalan-kan
python main.py
```

---

## Deploy ke Render (Free plan)

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python main.py`
- Tidak wajib set ENV (opsional). Semua toggle ada di `static_cfg.py`.
- **Health check & monitoring** (hemat bandwidth):
  - UptimeRobot: `HEAD https://<app>.onrender.com/healthz` (interval ≥5m)
  - Atau `GET https://<app>.onrender.com/botlive` dengan keyword `""alive":true"`

### Verifikasi setelah deploy
```powershell
$B="https://<app>.onrender.com"
(iwr "$B/uptime" -UseBasicParsing -TimeoutSec 10).Content
$stats=(iwr "$B/api/live/stats" -UseBasicParsing -TimeoutSec 10).Content | ConvertFrom-Json
$now=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds(); "fresh=" + ($now-[int]$stats.ts) + "s"
(iwr "$B/botlive" -UseBasicParsing -TimeoutSec 10).StatusCode   # 200
(iwr "$B/api/phish/phash" -UseBasicParsing -TimeoutSec 10).Content  # harus non-empty setelah autoload
```

---

## Operasional

- **Seeding awal**: cukup upload contoh‑contoh gambar phishing ke thread `imagephising`. Worker `phish_hash_autoreseed.py` akan meng‑**gabungkan** semuanya ke `SATPAMBOT_PHASH_DB_V1` saat startup.
- **Penambahan contoh baru**: setiap upload baru di thread itu, `phish_hash_inbox.py` otomatis **menambah** hash (tanpa duplikasi) dan update pesan DB.
- **Deteksi live**: runtime memuat daftar hash dan memeriksa pesan bergambar. Jika match (pHash/dHash/tile), tindakan pencegahan dilakukan sesuai kebijakan server/cog terkait.

---

## Troubleshooting cepat

- `/api/phish/phash` kosong `{"phash":[]}` → runtime belum memuat DB. **Restart service** atau pastikan file runtime **autoload** aktif.
- **Failed COG import** pada `phish_hash_inbox.py` → pastikan memakai versi *dependency-light* (tanpa `aiohttp`, gunakan `await attachment.read()`).
- Thread `imagephising` **tidak aktif** → kirim pesan di thread supaya aktif, lalu restart agar autoreseed bisa menemukan.

---

## Lisensi

Kode ini disediakan **sebagaimana adanya** untuk keperluan server pribadi. Pastikan mematuhi kebijakan Discord & hukum setempat.  
Hak cipta gambar/tautan milik masing‑masing pemiliknya.