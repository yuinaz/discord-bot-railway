
import os, logging, re, discord
from discord.ext import commands

log = logging.getLogger(__name__)

def _ids(s):
    out = set()
    for x in (s or "").replace(";", ",").split(","):
        x = x.strip()
        if x.isdigit():
            try: out.add(int(x))
            except: pass
    return out

def is_mod():
    names_env = (os.getenv("MOD_ROLE_NAMES") or "admin,administrator,moderator,mod,staff")
    NAMES = {n.strip().lower() for n in names_env.replace(";",",").split(",") if n.strip()}
    RID   = _ids(os.getenv("MOD_ROLE_IDS",""))
    UID   = _ids(os.getenv("MOD_USER_IDS",""))
    async def predicate(ctx: commands.Context):
        try:
            if ctx.author.id in UID: return True
            perms = getattr(ctx.author, "guild_permissions", None)
            if perms and (perms.administrator or perms.ban_members or perms.manage_messages):
                return True
            for r in getattr(ctx.author, "roles", []):
                if r.id in RID or (r.name or "").lower() in NAMES:
                    return True
        except Exception as e:
            log.warning("[tb_shim] mod check failed: %s", e)
        return False
    return commands.check(predicate)

def _pick_target(ctx: commands.Context, arg_text: str):
    # 1) reply target
    try:
        if ctx.message.reference and ctx.message.reference.resolved:
            msg = ctx.message.reference.resolved
            if hasattr(msg, "author"):
                return msg.author
    except Exception:
        pass
    # 2) mention or id in args
    if arg_text:
        m = re.search(r"<@!?(\d+)>", arg_text)
        if m:
            uid = int(m.group(1))
            u = ctx.guild.get_member(uid) if ctx.guild else None
            return u or discord.Object(id=uid)
        if arg_text.strip().isdigit():
            uid = int(arg_text.strip())
            u = ctx.guild.get_member(uid) if ctx.guild else None
            return u or discord.Object(id=uid)
    # 3) fallback: author
    return ctx.author

class TBShim(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="tb", aliases=["testban"], help="Simulasi ban yang aman: !tb [@user?] [alasan?]. Bisa reply pesan lalu ketik !tb")
    @is_mod()
    async def tb(self, ctx: commands.Context, *args):
        # pure simulation; tidak ada role-hierarchy/permission check pada target
        arg_text = " ".join(args)
        target = _pick_target(ctx, arg_text)
        alasan = None
        if arg_text:
            # hapus mention/id dari alasan agar lebih rapi
            alasan = re.sub(r"<@!?\d+>|^\d+", "", arg_text).strip() or None

        emb = discord.Embed(
            title="💀 Simulasi Ban oleh SatpamBot",
            description=(f"{getattr(target,'mention',str(target))} terdeteksi mengirim pesan mencurigakan.\n"
                         "(Pesan ini hanya simulasi untuk pengujian.)"),
            color=0x5865F2
        )
        if alasan:
            emb.add_field(name="Alasan", value=alasan, inline=False)
        emb.set_footer(text="Simulasi testban • Tidak ada aksi nyata yang dilakukan")

        try:
            await ctx.reply(embed=emb, mention_author=False)
        except Exception:
            await ctx.send(embed=emb)

async def setup(bot: commands.Bot):
    force = os.getenv("TB_FORCE_SHIM","0") == "1"
    try:
        # Jika diminta paksa, hapus command 'tb' yang sudah ada
        if force and "tb" in bot.all_commands:
            bot.remove_command("tb")
    except Exception as e:
        log.warning("[tb_shim] remove existing tb failed: %s", e)
    # Jika sudah ada 'tb' dan tidak force, biarkan (hindari konflik)
    if not force and "tb" in bot.all_commands:
        log.info("[tb_shim] existing 'tb' detected; shim not installed (set TB_FORCE_SHIM=1 to override).")
        return
    await bot.add_cog(TBShim(bot))
    log.info("[tb_shim] shim loaded%s", " (forced)" if force else "")
