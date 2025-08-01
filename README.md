# 🛡️ SatpamBot — Discord Anti-Phishing Bot with Dashboard + AI

SatpamBot adalah bot Discord anti-phishing modular yang dilengkapi dengan:
- 🧠 AI GPT-4 analysis
- 📊 Dashboard real-time (Flask)
- 🔐 Integrasi Google Safe Browsing & VirusTotal
- ⚔️ Auto-ban phishing links
- ✨ Logging ke 3 channel + database
- 🎨 Editor file + whitelist domain via web

---

## 🚀 Fitur Utama

| Fitur                            | Status |
|----------------------------------|--------|
| Deteksi phishing via teks        | ✅     |
| OCR Gambar anti phising          | ✅     |
| GPT-4 integrasi (`!gpt`)         | ✅     |
| Whitelist/Blacklist domain       | ✅     |
| Dashboard statistik Flask        | ✅     |
| Editor `main.py` & whitelist     | ✅     |
| Notifikasi Embed + Stiker        | ✅     |
| Google Safe Browsing API         | ✅     |
| VirusTotal API                   | ✅     |
| Logging ke SQLite                | ✅     |
| Auto update via GitHub           | ✅     |
| Webhook & Notifikasi Bot Mati    | ✅     |

---

## 📦 Instalasi Lokal

```bash
git clone https://github.com/yuinaz/discord-bot-railway.git
cd discord-bot-railway

python -m venv venv
venv\Scripts\activate   # ← Windows
# source venv/bin/activate  ← Linux/macOS

pip install -r requirements.txt
copy .env.example .env
# isi .env sesuai kebutuhan
python main.py
```

---

## 🌐 Deployment ke Render.com

1. Deploy sebagai **Web Service** (Python 3.10+)
2. Gunakan `main.py` sebagai entrypoint
3. Tambahkan `Environment Variables` dari `.env`
4. Aktifkan auto-deploy dari GitHub (opsional)

📌 Endpoint `/ping` digunakan untuk monitoring oleh UptimeRobot.

---

## 🔐 Contoh `.env`

```env
DISCORD_TOKEN=your_bot_token
FLASK_SECRET=your_flask_secret
CLIENT_ID=discord_client_id
CLIENT_SECRET=discord_client_secret
OAUTH_REDIRECT_URI=https://your.render.app/callback
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4
GOOGLE_SAFE_BROWSING_KEY=your_google_key
VIRUSTOTAL_API_KEY=your_vt_key
PORT=8080
ADMIN_IDS=123456789012345678
```

---

## 🧠 Command Utama

| Command       | Deskripsi                            |
|---------------|----------------------------------------|
| `!gpt prompt` | Menjawab dengan GPT-4 (hanya admin)    |
| `!servers`    | Menampilkan server yang terhubung      |

---

## 📂 Struktur Modular

```
📦 modules/
 ┣ 📜 discord_bot.py
 ┣ 📜 phishing_filter.py
 ┣ 📜 database.py
 ┣ 📜 gpt_chat.py
 ┣ 📜 logger.py
 ┗ 📜 utils.py
📂 templates/ → halaman dashboard Flask
```

---

## 🤖 Dibuat oleh

Made with ❤️ by [`@yuinaz`](https://github.com/yuinaz)