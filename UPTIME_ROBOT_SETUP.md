
# 🌐 Setup UptimeRobot untuk SatpamBot (Render.com)

Render.com (free tier) memiliki batasan waktu aktif dan bisa **masuk ke mode sleep** setelah beberapa menit tidak ada trafik. Untuk memastikan bot tetap aktif 24/7, gunakan layanan UptimeRobot.

---

## 🛠 Langkah-langkah Setup

### 1. Kunjungi UptimeRobot
👉 https://uptimerobot.com/

### 2. Buat Akun (Gratis)
- Daftar dengan email aktif
- Login ke dashboard UptimeRobot

### 3. Tambahkan Monitor Baru
- Klik tombol **"+ Add Monitor"**

### 4. Isi Detail Monitor:
| Field           | Isi                                              |
|-----------------|---------------------------------------------------|
| **Monitor Type**| HTTP(s)                                          |
| **Friendly Name** | SatpamBot Ping                                  |
| **URL (or IP)** | `https://satpambot.onrender.com/ping`            |
| **Monitoring Interval** | Every 5 minutes (default)               |

✅ Centang "Alert Contacts" untuk menerima email jika server mati (opsional)

---

## 🔁 Apa yang Dilakukan?
- UptimeRobot akan ping ke endpoint `/ping` setiap 5 menit.
- Ini **menjaga layanan Web Service tetap aktif** di Render.
- Membantu Flask app dan Discord bot tetap jalan.

---

## 🧪 Cek Manual
Buka di browser:
```
https://satpambot.onrender.com/ping
```

Harus menampilkan:
```
✅ Bot is alive!
```

---

## 💡 Tips Tambahan
- Pastikan `main.py` kamu memanggil `keep_alive()` saat startup
- Gunakan `PORT` yang sesuai di `utils.py`
- Jangan lupa tambahkan file `.env` di Render jika perlu webhook crash

---

## 👍 Done!
Sekarang bot kamu akan tetap hidup 24/7 meskipun Render.com masuk mode gratisan 🎉
