# SatpamBot 🚨

**SatpamBot** adalah bot Discord + dashboard web untuk menjaga server dari spam & phishing secara otomatis.  
Bot ini dilengkapi **dashboard modern** dengan **login glassmorphism + animasi**, serta kontrol keamanan yang bisa diatur realtime.

---

## ✨ Fitur Utama

- **🤖 Bot Discord**
  - Auto-ban pengguna yang mengirim gambar phishing (pHash detection).
  - Anti-link phishing dengan whitelist domain (Facebook, TikTok, dll).
  - Ban log rapi di thread khusus `#log-botphishing`.
  - Presence status sticky dengan jam lokal (Asia/Jakarta).
  - Command `!whitelist` langsung update whitelist realtime.

- **📊 Dashboard Web**
  - Login modern (glassmorphism + animasi partikel).
  - Tab **Security**:
    - Toggle Autoban Phishing.
    - Slider ambang batas pHash.
    - Editor Whitelist Domain (realtime).
    - Pengaturan tampilan Login (Logo, Background, Particles).
  - Tab **Phish Lab**: drag & drop gambar untuk dites apakah terdeteksi phishing.
  - Mini Monitor: realtime CPU, RAM, uptime.
  - Floating ban window: animasi daftar user yang baru dibanned.

- **⚙️ Konfigurasi via JSON (tanpa ENV tambahan)**
  - `data/ui_config.json` → Logo, background, animasi login.
  - `data/whitelist_domains.json` → daftar domain yang aman.
  - `data/phish_config.json` → ambang pHash & toggle autoban.

---

## 📥 Instalasi

### 1. Clone repo
```bash
git clone https://github.com/username/SatpamBot.git
cd SatpamBot
```

### 2. Buat virtualenv (opsional tapi direkomendasikan)
```bash
python -m venv venv
source venv/bin/activate   # Linux / Mac
venv\Scripts\activate      # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Konfigurasi ENV
Buat file `.env` di root:
```ini
DISCORD_TOKEN=xxx
GUILD_ID=1234567890
ADMIN_USER=admin
ADMIN_PASSWORD=supersecret
LOG_CHANNEL_ID=1234567890
TZ=Asia/Jakarta
```
*(Gunakan variabel ENV lama, patch terbaru tidak menambah ENV baru)*

### 5. Jalankan bot + dashboard
```bash
python main.py
```
Akses dashboard di:  
👉 `http://localhost:5000`

---

## 🖼️ Screenshot

### Login Page
![Login Page](docs/screenshots/login.png)

### Dashboard
![Dashboard](docs/screenshots/dashboard.png)

---

## 📂 Struktur Penting

```
SatpamBot/
├── satpambot/
│   ├── bot/
│   └── dashboard/
├── data/
│   ├── ui_config.json
│   ├── whitelist_domains.json
│   ├── phish_config.json
│   └── phish_phash.json
├── requirements.txt
└── main.py
```

---

## ⚡ Quick Config via Dashboard

- **Security tab** → toggle autoban, atur ambang pHash, edit whitelist, dan ganti tampilan login.
- **Phish Lab tab** → drag & drop gambar phishing untuk dites.
- **UI Config** tersimpan otomatis di `data/ui_config.json`.

---

## 📜 Lisensi
MIT License © 2025
