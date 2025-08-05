# 🛡️ SatpamBot - Discord Server Protection & Monitoring

SatpamBot adalah bot multifungsi untuk memantau, melindungi, dan mengelola server Discord Anda dari phishing, spam, dan aktivitas mencurigakan. Dilengkapi dengan dashboard modern, auto-ban keyword & gambar, serta integrasi AI Assistant.

## 🚀 Fitur Utama
- ✅ Auto-Ban Phishing (via keyword & OCR)
- ✅ Dashboard Admin Web (Flask)
- ✅ AI Assistant (OpenAI)
- ✅ Role & Channel Maker dari UI
- ✅ Logger, Notifikasi, Statistik Bot
- ✅ Live Chat Admin & Mobile Friendly
- ✅ Uptime Monitoring (UptimeRobot)
- ✅ Auto Update, Theme Switcher, Guest Mode

## 🛠️ Instalasi Lokal
```bash
git clone https://github.com/yuinaz/discord-bot-railway.git
cd discord-bot-railway
pip install -r requirements.txt
cp .env.example .env  # lalu isi token dan API key
python main.py
```

## 🌐 Deploy ke Render.com
1. Tambahkan file `Procfile` dan `keep_alive.py`
2. Gunakan `main.py` sebagai entrypoint
3. Pastikan `.env` berisi:
```
DISCORD_TOKEN=xxx
OPENAI_API_KEY=xxx
OCR_API_KEY=xxx
SECRET_KEY=somesecret
```

## 🧠 AI & OCR
- `OpenAI` digunakan untuk `/tanya`
- OCR via `https://ocr.space/` API (tidak butuh Tesseract lokal)

## 📁 Struktur Folder
- `modules/` - Semua route & logic
- `templates/` - HTML dashboard
- `static/` - CSS, JS, Assets
- `config/` - Tema dan setting JSON
- `data.db` - SQLite database bot

## 🤝 Kontribusi
Pull request dan masukan selalu diterima!

## 📜 Lisensi
MIT License © 2025 SatpamLeina
