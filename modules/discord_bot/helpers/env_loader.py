# env_loader (auto)
# Supports .env.local for local testing and .env.prod for production (Render)
import os
from pathlib import Path
from dotenv import load_dotenv

def load_env():
    # Do not override if already set by platform (Render dashboard envs)
    profile = os.getenv("ENV_PROFILE")  # "local" | "prod" | None
    cwd = Path(".")
    local_file = cwd / ".env.local"
    prod_file = cwd / ".env.prod"

    if profile == "local":
        if local_file.exists():
            load_dotenv(local_file, override=False)
        return "local"
    if profile == "prod":
        if prod_file.exists():
            load_dotenv(prod_file, override=False)
        return "prod"

    # Auto-detect: prefer Render provided envs; else fallback .env.local
    if os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID") or os.getenv("RENDER_INSTANCE_ID"):
        # On Render, try .env.prod if present but DO NOT override dashboard
        if prod_file.exists():
            load_dotenv(prod_file, override=False)
        return "prod"
    # Local default
    if local_file.exists():
        load_dotenv(local_file, override=False)
        return "local"
    return "none"
