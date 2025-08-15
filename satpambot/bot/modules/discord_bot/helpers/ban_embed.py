from discord import Embed, Colour
def build_ban_embed(target, *, reason=None, simulated=False):
    title = '💀 Simulasi Ban oleh SatpamBot' if simulated else '🔨 Ban oleh SatpamBot'
    desc  = f"{getattr(target,'mention',str(target))} terdeteksi mengirim pesan mencurigakan."
    if simulated: desc += '\n\n(Pesan ini hanya simulasi untuk pengujian.)'
    elif reason:  desc += f"\n\nAlasan: {reason}"
    emb = Embed(title=title, description=desc, colour=Colour.orange() if simulated else Colour.red())
    if simulated: emb.add_field(name='\u200b', value='🧪 Simulasi testban', inline=False)
    return emb
