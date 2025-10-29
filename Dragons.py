import os
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
import threading
from supabase import create_client, Client
from dotenv import load_dotenv
import datetime

# ==============================
# CARGAR VARIABLES DEL ENTORNO
# ==============================
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ==============================
# CONEXIÓN A SUPABASE
# ==============================
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==============================
# CONFIGURACIÓN DEL BOT
# ==============================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

start_time = datetime.datetime.utcnow()

# ==============================
# EMOJIS PERSONALIZADOS
# ==============================
EMOJI_DRAGON = "<a:Dragons:1432855339732177067>"
EMOJI_DERECHA = "<a:Derecha:1432857806754545685>"
EMOJI_IZQUIERDA = "<a:Izquierdo:1432857641029206086>"
EMOJI_FIRE = "<a:Fire:1432855375165526036>"
EMOJI_BOT = "<:Bot:1432856165234114702>"
EMOJI_PLANET = "<a:Planet:1432856726087925913>"
EMOJI_TIME = "<a:Time:1432856512660766770>"
EMOJI_MOD = "<a:Moderador:1432856982414561290>"
EMOJI_BAN = "<a:Ban:1432857189092950169>"
EMOJI_NOTES = "<a:Notas:1432881765000937483>"
EMOJI_ALERT = "<a:Alerta:1432884129044893748>"
EMOJI_WARNS = "<a:Warns:1432883811007467682>"
EMOJI_MUTE = "<a:Mute:1432898957595643945>"

# ==============================
# EVENTOS DE REGISTRO AUTOMÁTICO
# ==============================
@bot.event
async def on_guild_join(guild):
    """Registrar servidor cuando el bot entra"""
    try:
        supabase.table("servers").upsert({
            "guild_id": str(guild.id),
            "guild_name": guild.name,
            "joined_at": datetime.datetime.utcnow().isoformat()
        }).execute()
        print(f"✅ Servidor registrado: {guild.name}")
    except Exception as e:
        print(f"❌ Error registrando servidor: {e}")

@bot.event
async def on_member_join(member):
    """Enviar bienvenida y registrar usuario"""
    try:
        # Registrar usuario en Supabase
        supabase.table("usuarios").upsert({
            "user_id": str(member.id),
            "username": member.name,
            "joined_at": datetime.datetime.utcnow().isoformat()
        }).execute()

        # Buscar configuración de bienvenida
        guild_id = str(member.guild.id)
        data = supabase.table("bienvenidas").select("*").eq("guild_id", guild_id).execute()

        if data.data:
            config = data.data[0]
            canal = member.guild.get_channel(int(config["canal_id"]))
            if canal:
                embed = discord.Embed(
                    title=config["encabezado"],
                    description=config["texto"].replace("{usuario}", member.mention),
                    color=discord.Color.dark_red()
                )
                embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                embed.set_image(url=config["gif"])
                embed.set_footer(text="🐲 Dragons | Bienvenido al fuego eterno")
                await canal.send(embed=embed)

    except Exception as e:
        print(f"❌ Error en on_member_join: {e}")

# ==============================
# EVENTO DE INICIO
# ==============================
@bot.event
async def on_ready():
    print(f"🐉 El bot {bot.user} está activo y rugiendo.")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos sincronizados.")
    except Exception as e:
        print(f"❌ Error al sincronizar comandos: {e}")

# ==============================
# COMANDO /CREAR-BIENVENIDA
# ==============================
@bot.tree.command(name="crear-bienvenida", description="Crea una bienvenida personalizada para este servidor.")
@app_commands.describe(
    canal="Canal donde se enviará la bienvenida.",
    encabezado="Título del mensaje.",
    texto="Texto del mensaje (usa {usuario} para mencionar al nuevo miembro).",
    gif="URL del GIF o imagen."
)
async def crear_bienvenida(interaction: discord.Interaction, canal: discord.TextChannel, encabezado: str, texto: str, gif: str):
    guild_id = str(interaction.guild.id)

    try:
        supabase.table("bienvenidas").upsert({
            "guild_id": guild_id,
            "canal_id": canal.id,
            "encabezado": encabezado,
            "texto": texto,
            "gif": gif
        }).execute()

        embed = discord.Embed(
            title=f"{EMOJI_DRAGON} **[ DV ] Dragons Statistics**",
            description=f"**Canal:** {canal.mention}\n**Encabezado:** {encabezado}\n**Texto:** {texto}\n**GIF:** [Ver imagen]({gif})",
            color=discord.Color.blue()
        )
        embed.set_image(url=gif)
        embed.set_footer(text="Sistema de Bienvenida • Dragons")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error al guardar la configuración: {e}", ephemeral=True)

# ==============================
# COMANDO /BAN (solo administradores)
# ==============================
@bot.tree.command(name="ban", description="Banea a un usuario y lo guarda en la base de datos (solo admins).")
@app_commands.describe(usuario="Usuario a banear", motivo="Motivo del baneo")
async def ban(interaction: discord.Interaction, usuario: discord.Member, motivo: str):
    # 🔒 Verificación de permisos
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "🚫 No tienes permiso para usar este comando. Solo administradores pueden banear.",
            ephemeral=True
        )
        return

    try:
        await usuario.ban(reason=motivo)
        supabase.table("baneados").insert({
            "user_id": str(usuario.id),
            "username": usuario.name,
            "reason": motivo,
            "banned_at": datetime.datetime.utcnow().isoformat()
        }).execute()

        embed = discord.Embed(
            title=f"{EMOJI_BAN} Usuario Baneado",
            description=f"**{usuario.mention}** ha sido baneado.\n{EMOJI_NOTES} Motivo: **{motivo}**",
            color=discord.Color.red()
        )
        embed.set_footer(text="Sistema de Moderación • Dragons")
        await interaction.response.send_message(embed=embed)

        # DM opcional al usuario baneado
        try:
            dm_embed = discord.Embed(
                title=f"{EMOJI_ALERT} Has sido baneado de {interaction.guild.name}",
                description=f"**Motivo:** {motivo}",
                color=discord.Color.blue()
            )
            await usuario.send(embed=dm_embed)
        except:
            pass

    except Exception as e:
        await interaction.response.send_message(f"❌ Error al banear: {e}", ephemeral=True)

# ==============================
# COMANDO /ELIMINAR BAN (solo administradores)
# ==============================

@bot.tree.command(name="unban", description="Desbanea a un usuario (solo administradores).")
@app_commands.describe(usuario="ID del usuario que deseas desbanear")
@app_commands.checks.has_permissions(administrator=True)
async def eliminar_ban(interaction: discord.Interaction, usuario: str):
    try:
        # Verificar si el usuario tiene permisos de administrador
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("🚫 No tienes permisos para usar este comando.", ephemeral=True)
            return

        user = await bot.fetch_user(int(usuario))
        await interaction.guild.unban(user)

        embed = discord.Embed(
            title=f" {EMOJI_ALERT} Usuario Desbaneado",
            description=f"El usuario **{user.name}** ha sido desbaneado correctamente.",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Acción realizada por: {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    except discord.NotFound:
        await interaction.response.send_message("No se encontró ese usuario en la lista de baneos.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ocurrió un error: {e}", ephemeral=True)


# ==============================
# COMANDO /WARN
# ==============================
@bot.tree.command(name="warn", description="Advierte a un usuario y guarda la advertencia en Supabase (solo admins).")
@app_commands.describe(usuario="Usuario a advertir", motivo="Motivo de la advertencia")
async def warn(interaction: discord.Interaction, usuario: discord.Member, motivo: str):
    # 🔒 Verificación de permisos
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "No tienes permiso para usar este comando. Solo administradores pueden advertir.",
            ephemeral=True
        )
        return

    try:
        # Guardar advertencia en Supabase
        supabase.table("warns").insert({
            "user_id": str(usuario.id),
            "username": usuario.name,
            "reason": motivo,
            "warned_by": interaction.user.name
        }).execute()

        # Crear embed de confirmación
        embed = discord.Embed(
            title=f"{EMOJI_ALERT} Usuario Advertido",
            description=(
                f"{EMOJI_NOTES} **Usuario:** {usuario.mention}\n"
                f"{EMOJI_FIRE} **Motivo:** {motivo}\n"
                f"{EMOJI_BOT} **Moderador:** {interaction.user.mention}"
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Sistema de Advertencias • Dragons")
        await interaction.response.send_message(embed=embed)

        # Intentar enviar DM al usuario advertido
        try:
            dm_embed = discord.Embed(
                title=f"{EMOJI_ALERT} Has sido advertido en {interaction.guild.name}",
                description=f"**Motivo:** {motivo}\n**Moderador:** {interaction.user.name}",
                color=discord.Color.blue()
            )
            dm_embed.set_footer(text="Sistema de Advertencias • Dragons")
            await usuario.send(embed=dm_embed)
        except:
            pass  # si el usuario tiene los DMs cerrados, ignorar el error

    except Exception as e:
        await interaction.response.send_message(f"❌ Error al registrar la advertencia: {e}", ephemeral=True)



# ==============================
# COMANDO /VER-WARNS
# ==============================
@bot.tree.command(name="warnings", description="Muestra las advertencias registradas de un usuario.")
@app_commands.describe(usuario="Usuario del que deseas ver las advertencias")
async def ver_warns(interaction: discord.Interaction, usuario: discord.Member):
    try:
        data = supabase.table("warns").select("*").eq("user_id", str(usuario.id)).execute()

        if not data.data:
            await interaction.response.send_message(f"✅ {usuario.mention} no tiene advertencias registradas.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"{EMOJI_NOTES} Advertencias de {usuario.name}",
            color=discord.Color.blue()
        )

        for warn in data.data:
            fecha = warn["warned_at"][:19].replace("T", " ")
            embed.add_field(
                name=f"{EMOJI_FIRE} Motivo: {warn['reason']}",
                value=f"{EMOJI_MOD} Por: **{warn['warned_by']}**\n🕓 {fecha}",
                inline=False
            )

        embed.set_footer(text="Sistema de Advertencias • Dragons")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error al obtener advertencias: {e}", ephemeral=True)

# ==============================
# COMANDO /ELIMINAR-WARN (solo administradores)
# ==============================
@bot.tree.command(name="unwarns", description="Elimina una advertencia específica o todas las de un usuario (solo admins).")
@app_commands.describe(
    usuario="Usuario del que deseas eliminar advertencias",
    warn_id="ID de la advertencia a eliminar (déjalo vacío para eliminar todas)"
)
async def eliminar_warn(interaction: discord.Interaction, usuario: discord.Member, warn_id: int = None):
    # 🔒 Verificación de permisos
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "🚫 No tienes permiso para usar este comando. Solo administradores pueden eliminar advertencias.",
            ephemeral=True
        )
        return

    try:
        if warn_id:
            # Eliminar una advertencia específica
            response = supabase.table("warns").delete().eq("id", warn_id).eq("user_id", str(usuario.id)).execute()

            if response.data:
                embed = discord.Embed(
                    title=f"{EMOJI_ALERT} Advertencia Eliminada",
                    description=f"⚙️ Se eliminó la advertencia con ID **{warn_id}** del usuario {usuario.mention}.",
                    color=discord.Color.red()
                )
                embed.set_footer(text="Sistema de Advertencias • Dragons")
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(f"❌ No se encontró una advertencia con ID {warn_id} para {usuario.mention}.", ephemeral=True)

        else:
            # Eliminar todas las advertencias de un usuario
            response = supabase.table("warns").delete().eq("user_id", str(usuario.id)).execute()
            total = len(response.data)

            embed = discord.Embed(
                title=f"{EMOJI_FIRE} Advertencias Eliminadas",
                description=f"{EMOJI_DRAGON} Se eliminaron **{total}** advertencias de {usuario.mention}.",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Sistema de Advertencias • Dragons")
            await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error al eliminar advertencias: {e}", ephemeral=True)


# ==============================
# COMANDO /BOTSTATISTICS
# ==============================
@bot.tree.command(name="botstatistics", description="📊 Muestra las estadísticas globales del bot Dragons")
async def bot_statistics(interaction: discord.Interaction):
    try:
        total_baneados = len(supabase.table("baneados").select("id").execute().data)
        total_usuarios = len(supabase.table("usuarios").select("id").execute().data)
        total_servers = len(supabase.table("servers").select("id").execute().data)

        uptime = datetime.datetime.utcnow() - start_time
        days, remainder = divmod(int(uptime.total_seconds()), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

        embed = discord.Embed(
            title=f"{EMOJI_DERECHA} **[ DV ] Dragons Statistics** {EMOJI_IZQUIERDA}",
            description=f"{EMOJI_BOT} **Estadísticas en tiempo real**",
            color=discord.Color.purple()
        )
        embed.add_field(name=f"{EMOJI_BAN}  Usuarios Baneados", value=f"**{total_baneados}**", inline=True)
        embed.add_field(name=f"{EMOJI_PLANET}  Usuarios Globales", value=f"**{total_usuarios}**", inline=True)
        embed.add_field(name=f"{EMOJI_MOD}  Servidores Activos", value=f"**{total_servers}**", inline=True)
        embed.add_field(name=f"{EMOJI_TIME}  Tiempo Activo", value=f"**{uptime_str}**", inline=False)

        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1432855339732177067.webp")
        embed.set_footer(text="⚙️ Powered by Dragons Development", icon_url="https://cdn.discordapp.com/emojis/1432855375165526036.webp")

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error al obtener estadísticas: {e}", ephemeral=True)

# ==============================
# COMANDO /MUTE (solo administradores)
# ==============================

@bot.tree.command(name="mute", description="Silencia a un usuario temporalmente (solo administradores).")
@app_commands.describe(
    usuario="Usuario que será silenciado",
    minutos="Duración del silencio en minutos",
    motivo="Motivo del mute"
)
@app_commands.checks.has_permissions(administrator=True)
async def mute(interaction: discord.Interaction, usuario: discord.Member, minutos: int, motivo: str = "No especificado"):
    import datetime
    import discord

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 No tienes permisos para usar este comando.", ephemeral=True)
        return

    if usuario == interaction.user:
        await interaction.response.send_message("❌ No puedes mutearte a ti mismo.", ephemeral=True)
        return

    if usuario.guild_permissions.administrator:
        await interaction.response.send_message("⚠️ No puedes silenciar a otro administrador.", ephemeral=True)
        return

    try:
        duracion = datetime.timedelta(minutes=minutos)
        await usuario.timeout(discord.utils.utcnow() + duracion, reason=motivo)

        embed = discord.Embed(
            title=f"{EMOJI_MUTE} Usuario Silenciado",
            description=(
                f"**{EMOJI_DERECHA} Usuario:** {usuario.mention}\n"
                f"**{EMOJI_TIME} Duración:** {minutos} minutos\n"
                f"**{EMOJI_TIME} Motivo:** {motivo}"
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Silenciado por {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()

        await interaction.response.send_message(embed=embed)

        try:
            embed_dm = discord.Embed(
                title=f" {EMOJI_MUTE} Has sido silenciado",
                description=(
                    f"{EMOJI_MOD} Has sido silenciado en **{interaction.guild.name}** por **{minutos} minutos**.\n"
                    f"{EMOJI_NOTES} **Motivo:** {motivo}"
                ),
                color=discord.Color.dark_red()
            )
            await usuario.send(embed=embed_dm)
        except:
            pass

    except Exception as e:
        await interaction.response.send_message(f"❌ Error al aplicar el mute: `{e}`", ephemeral=True)

# ==============================
# COMANDO /MUTE (solo administradores)
# ==============================

@bot.tree.command(name="unmute", description="Quita el silencio de un usuario (solo administradores).")
@app_commands.describe(
    usuario="Usuario al que se le quitará el silencio",
    motivo="Motivo para quitar el mute"
)
@app_commands.checks.has_permissions(administrator=True)
async def unmute(interaction: discord.Interaction, usuario: discord.Member, motivo: str = "No especificado"):
    import datetime
    import discord

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 No tienes permisos para usar este comando.", ephemeral=True)
        return

    if usuario == interaction.user:
        await interaction.response.send_message("❌ No puedes modificar tu propio silencio.", ephemeral=True)
        return

    try:
        # Quitar el mute (timeout)
        await usuario.timeout(None, reason=motivo)

        embed = discord.Embed(
            title=f"{EMOJI_ALERT} Usuario Desmuteado",
            description=(
                f"**{EMOJI_DRAGON} Usuario:** {usuario.mention}\n"
                f"**{EMOJI_NOTES} Motivo:** {motivo}"
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Desmuteado por {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()

        await interaction.response.send_message(embed=embed)

        # Mensaje directo al usuario
        try:
            embed_dm = discord.Embed(
                title="🔊 Se te ha quitado el silencio",
                description=(
                    f"Tu silencio en **{interaction.guild.name}** ha sido levantado.\n"
                    f"**Motivo:** {motivo}"
                ),
                color=discord.Color.green()
            )
            await usuario.send(embed=embed_dm)
        except:
            pass

    except Exception as e:
        await interaction.response.send_message(f"❌ Error al quitar el mute: `{e}`", ephemeral=True)

# ==============================
# COMANDO /PERFIL (solo administradores)
# ==============================

@bot.tree.command(name="userinfo", description="Muestra tu perfil o el de otro usuario.")
@app_commands.describe(usuario="Usuario a consultar (opcional)")
async def perfil(interaction: discord.Interaction, usuario: discord.Member = None):
    import datetime
    if usuario is None:
        usuario = interaction.user

    # Buscar warns del usuario en Supabase
    warns_data = supabase.table("warns").select("*").eq("user_id", str(usuario.id)).execute()
    total_warns = len(warns_data.data) if warns_data.data else 0

    # Calcular días en el servidor
    joined_days = (datetime.datetime.utcnow() - usuario.joined_at.replace(tzinfo=None)).days

    embed = discord.Embed(
        title=f"👤 Perfil de {usuario.name}",
        description=(
            f"**{EMOJI_FIRE} ID:** `{usuario.id}`\n"
            f"**{EMOJI_DRAGON} Se unió hace:** `{joined_days}` días\n"
            f"**{EMOJI_ALERT} Advertencias:** `{total_warns}`\n"
            f"**{EMOJI_NOTES} Servidor:** {interaction.guild.name}\n\n"
            f"{EMOJI_DRAGON} *Usuario registrado en Dragons System*"
        ),
        color=discord.Color.blue()
    )

    embed.set_thumbnail(url=usuario.display_avatar.url)
    embed.set_footer(text=f"Consulta realizada por {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
    embed.timestamp = datetime.datetime.utcnow()

    await interaction.response.send_message(embed=embed)

# ==============================
# MINI SERVIDOR FLASK PARA RENDER
# ==============================
app = Flask("")

@app.route("/")
def home():
    return "🐉 Bot activo en Render (Dragons)"

def run():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

threading.Thread(target=run).start()

# ==============================
# INICIAR BOT
# ==============================
if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
else:
    print("❌ ERROR: No se encontró DISCORD_TOKEN en el entorno.")
