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
            color=discord.Color.green()
        )
        embed.set_image(url=gif)
        embed.set_footer(text="Sistema de Bienvenida • Dragons")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error al guardar la configuración: {e}", ephemeral=True)

# ==============================
# COMANDO /BAN
# ==============================
@bot.tree.command(name="ban", description="Banea a un usuario y lo guarda en la base de datos.")
@app_commands.describe(usuario="Usuario a banear", motivo="Motivo del baneo")
async def ban(interaction: discord.Interaction, usuario: discord.Member, motivo: str):
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
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error al banear: {e}", ephemeral=True)

# ==============================
# COMANDO /WARN
# ==============================
@bot.tree.command(name="warn", description="Advierte a un usuario y guarda la advertencia en Supabase.")
@app_commands.describe(usuario="Usuario a advertir", motivo="Motivo de la advertencia")
async def warn(interaction: discord.Interaction, usuario: discord.Member, motivo: str):
    try:
        # Insertar advertencia en Supabase
        supabase.table("warns").insert({
            "user_id": str(usuario.id),
            "username": usuario.name,
            "reason": motivo,
            "warned_by": interaction.user.name
        }).execute()

        embed = discord.Embed(
            title=f"{EMOJI_WARNS} Usuario Advertido",
            description=f"{EMOJI_NOTES} **Usuario:** {usuario.mention}\n{EMOJI_FIRE} **Motivo:** {motivo}\n{EMOJI_BOT} **Moderador:** {interaction.user.mention}",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)

        # Enviar DM al usuario advertido
        try:
            dm_embed = discord.Embed(
                title=f" {EMOJI_ALERT}⚠️ Has sido advertido en {interaction.guild.name}",
                description=f"**Motivo:** {motivo}\n**Moderador:** {interaction.user.name}",
                color=discord.Color.orange()
            )
            await usuario.send(embed=dm_embed)
        except:
            pass

    except Exception as e:
        await interaction.response.send_message(f"❌ Error al registrar la advertencia: {e}", ephemeral=True)


# ==============================
# COMANDO /VER-WARNS
# ==============================
@bot.tree.command(name="ver-warns", description="Muestra las advertencias registradas de un usuario.")
@app_commands.describe(usuario="Usuario del que deseas ver las advertencias")
async def ver_warns(interaction: discord.Interaction, usuario: discord.Member):
    try:
        data = supabase.table("warns").select("*").eq("user_id", str(usuario.id)).execute()

        if not data.data:
            await interaction.response.send_message(f"✅ {usuario.mention} no tiene advertencias registradas.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"{EMOJI_NOTES} Advertencias de {usuario.name}",
            color=discord.Color.gold()
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
