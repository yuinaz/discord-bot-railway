
import discord
from modules.discord_bot import bot

async def notify_ngobrol_ban(guild, member):
    ngobrol_channel_id = 886534544688308265  # Channel 💬︲ngobrol
    channel = guild.get_channel(ngobrol_channel_id)
    if not channel:
        return
    embed = discord.Embed(
        title="🚨 Phishing Attempt Detected!",
        description=f"😈 **{member.mention}** mencoba menyebarkan link phishing dan langsung ditendang! 😂",
        color=discord.Color.red()
    )
    embed.set_image(url="https://media.discordapp.net/stickers/902893867103944744.webp?size=160")  # FibiLaugh
    await channel.send(embed=embed)
