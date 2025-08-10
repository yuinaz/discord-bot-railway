import os
import json

REQUIRED_ENV_KEYS = [
    "DISCORD_TOKEN",
    "SECRET_KEY",
]

REQUIRED_FILES = [
    ".env",
    "superadmin.db",
    "settings.json",
    "templates/login.html",
    "templates/dashboard.html",
    "main.py",
    "modules/oauth.py",
    "modules/discord_bot.py",
]

def check_env():
    print("📦 Mengecek file `.env`...")
    if not os.path.exists(".env"):
        print("❌ File `.env` tidak ditemukan.")
        return False

    with open(".env", "r", encoding="utf-8") as f:
        content = f.read()
        missing = [key for key in REQUIRED_ENV_KEYS if key not in content]
        if missing:
            print(f"❌ Variable berikut hilang di `.env`: {missing}")
            return False
    print("✅ `.env` lengkap.")
    return True

def check_files():
    print("\n📦 Mengecek file dan folder penting...")
    missing = []
    for path in REQUIRED_FILES:
        if not os.path.exists(path):
            missing.append(path)

    if missing:
        print("❌ File berikut tidak ditemukan:")
        for m in missing:
            print(f"   - {m}")
        return False

    print("✅ Semua file penting ditemukan.")
    return True

def check_theme_config():
    print("\n🎨 Mengecek konfigurasi tema...")
    if not os.path.exists("config/theme.json"):
        print("⚠️ File tema tidak ditemukan, membuat default...")
        os.makedirs("config", exist_ok=True)
        with open("config/theme.json", "w", encoding="utf-8") as f:
            json.dump({"theme": "default"}, f, indent=2)
        print("✅ `config/theme.json` dibuat dengan tema default.")
    else:
        print("✅ `config/theme.json` sudah ada.")

if __name__ == "__main__":
    ok_env = check_env()
    ok_files = check_files()
    check_theme_config()

    if ok_env and ok_files:
        print("\n🎉 Semua persyaratan sudah terpenuhi. Siap untuk dijalankan!")
    else:
        print("\n⚠️ Ada yang belum lengkap. Silakan lengkapi dulu sebelum run.")
