
import discord

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
    await channel.send(embed=embed)

    for sticker in guild.stickers:
        if sticker.name.lower() == "fibilaugh":
            await channel.send(sticker=sticker)
            break
