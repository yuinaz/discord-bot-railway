# 🚨 SatpamBot - Discord Security Dashboard with AI, Logging, and Monitoring

SatpamBot adalah bot keamanan server Discord yang dilengkapi dengan **dashboard modern**, **AI phishing detection**, **backup otomatis**, dan **fitur logging real-time**. Dirancang untuk komunitas yang ingin menjaga keamanan, transparansi, dan kontrol penuh atas server Discord mereka.

---

## ✨ Fitur Utama

### 🔐 Autentikasi & Dashboard
- Login berbasis password admin
- "See as Guest" mode untuk melihat dashboard tanpa login
- Tema gelap/terang + switcher visual

### 📊 Monitoring & Statistik
- Grafik aktivitas server (Uptime, CPU, RAM)
- Live heatmap aktivitas
- Server Insights (jumlah user, channel, response time)

### 🤖 Discord Bot
- Menampilkan status online & notifikasi otomatis ke channel `#mod-command`
- Command `!status`, `!poll`, `!closepoll`
- Polling interaktif berbasis tombol
- Logging aktivitas pengguna
- Deteksi otomatis phishing link
- Peringatan dan ban otomatis pengguna yang mencurigakan

### 📁 Backup & Restore
- Auto-backup berkala data penting
- Manual restore & export data
- Penyimpanan lokal dalam folder `/backup`

### 🛡️ Whitelist & Phishing Filter
- Sistem whitelist untuk bypass deteksi
- AI-powered phishing detection (integrasi OpenAI)
- Logging user yang terkena filter

### 🧠 AI Assistant
- Fitur `/tanya` di dashboard (chatbot AI)
- Bisa digunakan untuk tanya jawab atau bantuan teknis

### 📥 Logger Real-Time
- Panel admin untuk melihat:
  - Siapa yang login
  - Siapa yang diban
  - Aktivitas command di Discord
- Logging ke file `logs/error.log`

### 🛠️ Fitur Lain
- Editor online untuk file Python
- Updater otomatis dari dashboard
- Role & Channel Maker langsung dari UI
- Tema visual neon cyberpunk + animasi
- Mobile-friendly UI

---

## 🧩 Struktur Folder

```
.
├── main.py
├── .env
├── logs/
│   └── error.log
├── data/
│   ├── theme.json
│   └── whitelist.json
├── backup/
│   └── [file cadangan]
├── templates/
│   └── *.html
├── static/
│   └── css/, js/, icon/
├── modules/
│   ├── dashboard.py
│   ├── discord_bot.py
│   ├── phishing_filter.py
│   ├── logger.py
│   ├── backup.py
│   ├── updater.py
│   └── ...
```

---

## ⚙️ Instalasi & Jalankan

### 1. Clone Repo & Install Dependencies

```bash
git clone https://github.com/yuinaz/satpambot
cd satpambot
pip install -r requirements.txt
```

### 2. Buat File `.env`

```env
DISCORD_TOKEN=your_discord_bot_token
SECRET_KEY=sessiooonkey123
DEBUG=false
RENDER=true
OPENAI_API_KEY=sk-...
```

### 3. Jalankan Bot + Dashboard

```bash
python main.py
```

Bot & Flask dashboard akan otomatis aktif.

---

## 🚀 Deployment

SatpamBot dapat dijalankan di:
- 🌐 [Render.com](https://render.com/)
- 💻 VPS Ubuntu / Windows
- ☁️ UptimeRobot (ping monitor)

---

## 📸 Screenshot Dashboard

*(tambahkan screenshot nanti jika diinginkan)*

---

## 📜 Lisensi

Proyek ini bersifat open source dan didistribusikan di bawah lisensi MIT.

---

## 🙋 FAQ

**Q: Apakah bisa digunakan tanpa login?**  
A: Bisa. Ada fitur "See as Guest" untuk melihat semua statistik (read-only).

**Q: Bot saya tidak muncul sebagai online di Discord?**  
A: Pastikan `DISCORD_TOKEN` valid, `intents` aktif, dan channel `#mod-command` tersedia.

**Q: Apakah mendukung tema kustom?**  
A: Ya, dashboard mendukung switching tema visual (dark/light/neon).

---

## 🤝 Kontribusi

Pull request dan ide baru sangat diterima. Jika Anda punya saran fitur tambahan, silakan buka [issue](https://github.com/yuinaz/satpambot/issues) baru.