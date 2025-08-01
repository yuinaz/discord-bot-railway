
import os
import shutil
import datetime

def backup_settings():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    os.makedirs("backups", exist_ok=True)
    try:
        shutil.copy("settings.json", f"backups/settings_{today}.json")
        print(f"✅ Backup settings.json ke backups/settings_{today}.json")
    except Exception as e:
        print("❌ Gagal backup settings.json:", e)
