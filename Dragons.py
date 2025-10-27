import os
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
import threading
from supabase import create_client, Client
from dotenv import load_dotenv

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

    # Guardar en la base de datos Supabase
    try:
        supabase.table("bienvenidas").upsert({
            "guild_id": guild_id,
            "canal_id": canal.id,
            "encabezado": encabezado,
            "texto": texto,
            "gif": gif
        }).execute()

        embed = discord.Embed(
            title="🐲 ¡Bienvenida configurada con éxito!",
            description=f"**Canal:** {canal.mention}\n**Encabezado:** {encabezado}\n**Texto:** {texto}\n**GIF:** [Ver imagen]({gif})",
            color=discord.Color.green()
        )
        embed.set_image(url=gif)
        embed.set_footer(text="Sistema de Bienvenida • Dragons")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error al guardar la configuración: {e}", ephemeral=True)

# ==============================
# EVENTO DE ENTRADA DE USUARIOS
# ==============================
@bot.event
async def on_member_join(member):
    try:
        guild_id = str(member.guild.id)
        data = supabase.table("bienvenidas").select("*").eq("guild_id", guild_id).execute()

        if not data.data:
            return  # No hay configuración en este servidor

        config = data.data[0]
        canal = member.guild.get_channel(int(config["canal_id"]))
        if not canal:
            return

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
