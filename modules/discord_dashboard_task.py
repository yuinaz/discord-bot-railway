import os
import discord
from flask import current_app

async def handle_role_and_channel(bot):
    try:
        guild = discord.utils.get(bot.guilds)
        if not guild:
            return

        # Role
        role_data = current_app.config.get("create_role_data")
        if role_data:
            color = discord.Color(int(role_data['color'].lstrip('#'), 16))
            icon_data = None
            if role_data['icon']:
                path = os.path.join("satpambot_monitor_plus_modern", "static", "uploads", role_data['icon'])
                with open(path, "rb") as f:
                    icon_data = f.read()
            await guild.create_role(name=role_data['name'], color=color, icon=icon_data)
            print(f"[✅ BOT] Role '{role_data['name']}' dibuat dari dashboard.")
            current_app.config["create_role_data"] = None

        # Channel
        channel_data = current_app.config.get("create_channel_data")
        if channel_data:
            if channel_data['type'] == "text":
                await guild.create_text_channel(channel_data['name'])
            else:
                await guild.create_voice_channel(channel_data['name'])
            print(f"[✅ BOT] Channel '{channel_data['name']}' dibuat.")
            current_app.config["create_channel_data"] = None

    except Exception as e:
        print("[❌ BOT ERROR] Saat buat role/channel:", e)