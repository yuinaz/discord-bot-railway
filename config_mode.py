import os
from dotenv import load_dotenv

APP_MODE = os.getenv("APP_MODE")

if APP_MODE != "production":
    # Untuk lokal, load dari file
    load_dotenv(".env.local")

# Pastikan variabel penting ada
required_vars = ["DISCORD_TOKEN", "SECRET_KEY", "CLIENT_ID", "CLIENT_SECRET"]
missing = [var for var in required_vars if not os.getenv(var)]
if missing:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
