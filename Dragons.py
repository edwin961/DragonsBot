import os
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
import threading
from supabase import create_client, Client
from dotenv import load_dotenv
import datetime
import aiohttp
from discord import PermissionOverwrite, Permissions, Colour
from discord.ext import commands
import json

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
EMOJI_WELCOME = "<a:Welcome:1433493464456105984>"
EMOJI_TICKET = "🎫"
EMOJI_LOCK = "🔒"
EMOJI_UNLOCK = "🔓"
EMOJI_CLOSE = "❌"

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
    gif="URL del GIF o imagen.",
    color="Color del embed en formato hexadecimal (ejemplo: #4169e1 o 4169e1)"
)
async def crear_bienvenida(interaction: discord.Interaction, canal: discord.TextChannel, encabezado: str, texto: str, gif: str, color: str = "#0099ff"):
    guild_id = str(interaction.guild.id)

    # Limpiar el color (remover # si existe y validar)
    color_limpio = color.lstrip('#')
    
    # Validar que sea un color hexadecimal válido
    if len(color_limpio) != 6 or not all(c in '0123456789abcdefABCDEF' for c in color_limpio):
        await interaction.response.send_message(
            "❌ **Color inválido.** Usa un formato hexadecimal válido.\n"
            "**Ejemplos:** `#4169e1`, `4169e1`, `#ff0000`, `00ff00`",
            ephemeral=True
        )
        return

    try:
        # Convertir hex a color de Discord
        color_int = int(color_limpio, 16)
        color_embed = discord.Color(color_int)

        supabase.table("bienvenidas").upsert({
            "guild_id": guild_id,
            "canal_id": canal.id,
            "encabezado": encabezado,
            "texto": texto,
            "gif": gif,
            "color": color_limpio
        }).execute()

        embed = discord.Embed(
            title=f"{EMOJI_DRAGON} **[ DV ] Dragons Statistics**",
            description=f"**Canal:** {canal.mention}\n**Encabezado:** {encabezado}\n**Texto:** {texto}\n**Color:** `#{color_limpio}`\n**GIF:** [Ver imagen]({gif})",
            color=color_embed
        )
        embed.set_image(url=gif)
        embed.set_footer(text="Sistema de Bienvenida • Dragons")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error al guardar la configuración: {e}", ephemeral=True)

# ==============================
# SISTEMA DE TICKETS - CONFIGURACIÓN
# ==============================

@bot.tree.command(name="ticket-config", description="Configura el sistema de tickets (solo administradores)")
@app_commands.describe(
    categoria="Categoría donde se crearán los tickets",
    canal_logs="Canal donde se registrarán los logs de tickets",
    rol_soporte="Rol que podrá ver los tickets",
    titulo="Título del embed de tickets",
    descripcion="Descripción del embed",
    color="Color del embed (hex, ej: #4169e1)"
)
@app_commands.checks.has_permissions(administrator=True)
async def ticket_config(
    interaction: discord.Interaction,
    categoria: discord.CategoryChannel,
    canal_logs: discord.TextChannel,
    rol_soporte: discord.Role,
    titulo: str = "🎫 Sistema de Tickets",
    descripcion: str = "Haz clic en el botón para crear un ticket",
    color: str = "#4169e1"
):
    guild_id = str(interaction.guild.id)
    color_limpio = color.lstrip('#')
    
    if len(color_limpio) != 6 or not all(c in '0123456789abcdefABCDEF' for c in color_limpio):
        await interaction.response.send_message("❌ Color inválido. Usa formato hexadecimal.", ephemeral=True)
        return

    try:
        # Guardar configuración en Supabase
        supabase.table("ticket_config").upsert({
            "guild_id": guild_id,
            "categoria_id": str(categoria.id),
            "canal_logs_id": str(canal_logs.id),
            "rol_soporte_id": str(rol_soporte.id),
            "titulo": titulo,
            "descripcion": descripcion,
            "color": color_limpio
        }).execute()

        embed = discord.Embed(
            title=f"{EMOJI_TICKET} Configuración de Tickets Guardada",
            description=(
                f"**Categoría:** {categoria.mention}\n"
                f"**Canal de Logs:** {canal_logs.mention}\n"
                f"**Rol de Soporte:** {rol_soporte.mention}\n"
                f"**Título:** {titulo}\n"
                f"**Color:** `#{color_limpio}`"
            ),
            color=discord.Color(int(color_limpio, 16))
        )
        embed.set_footer(text="Sistema de Tickets • Dragons")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error al guardar configuración: {e}", ephemeral=True)


@bot.tree.command(name="ticket-panel", description="Crea el panel de tickets en este canal (solo administradores)")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_panel(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    
    try:
        # Obtener configuración
        config_data = supabase.table("ticket_config").select("*").eq("guild_id", guild_id).execute()
        
        if not config_data.data:
            await interaction.response.send_message(
                "❌ No hay configuración de tickets. Usa `/ticket-config` primero.",
                ephemeral=True
            )
            return
        
        config = config_data.data[0]
        color = discord.Color(int(config["color"], 16))
        
        # Crear embed del panel
        embed = discord.Embed(
            title=config["titulo"],
            description=config["descripcion"],
            color=color
        )
        embed.add_field(
            name=f"{EMOJI_FIRE} ¿Necesitas ayuda?",
            value="Presiona el botón de abajo para abrir un ticket.\nNuestro equipo te atenderá lo antes posible.",
            inline=False
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1432855339732177067.webp")
        embed.set_footer(text="Sistema de Tickets • Dragons")
        embed.timestamp = datetime.datetime.utcnow()
        
        # Crear botón
        view = TicketButton()
        
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Panel de tickets creado correctamente.", ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error al crear panel: {e}", ephemeral=True)


# ==============================
# BOTÓN PARA CREAR TICKETS
# ==============================
class TicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Crear Ticket", style=discord.ButtonStyle.green, emoji="🎫", custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)
        
        try:
            # Verificar si el usuario ya tiene un ticket abierto
            existing = supabase.table("tickets").select("*").eq("guild_id", guild_id).eq("user_id", user_id).eq("estado", "abierto").execute()
            
            if existing.data:
                await interaction.response.send_message(
                    f"❌ Ya tienes un ticket abierto: <#{existing.data[0]['canal_id']}>",
                    ephemeral=True
                )
                return
            
            # Obtener configuración
            config_data = supabase.table("ticket_config").select("*").eq("guild_id", guild_id).execute()
            
            if not config_data.data:
                await interaction.response.send_message(
                    "❌ El sistema de tickets no está configurado.",
                    ephemeral=True
                )
                return
            
            config = config_data.data[0]
            categoria = interaction.guild.get_channel(int(config["categoria_id"]))
            rol_soporte = interaction.guild.get_role(int(config["rol_soporte_id"]))
            
            # Crear canal del ticket
            overwrites = {
                interaction.guild.default_role: PermissionOverwrite(view_channel=False),
                interaction.user: PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                rol_soporte: PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                interaction.guild.me: PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
            }
            
            ticket_number = len(supabase.table("tickets").select("id").eq("guild_id", guild_id).execute().data) + 1
            canal_ticket = await categoria.create_text_channel(
                name=f"ticket-{ticket_number}-{interaction.user.name}",
                overwrites=overwrites
            )
            
            # Guardar en base de datos
            supabase.table("tickets").insert({
                "guild_id": guild_id,
                "user_id": user_id,
                "canal_id": str(canal_ticket.id),
                "numero": ticket_number,
                "estado": "abierto"
            }).execute()
            
            # Embed de bienvenida en el ticket
            embed_ticket = discord.Embed(
                title=f"{EMOJI_TICKET} Ticket #{ticket_number}",
                description=f"Hola {interaction.user.mention}, bienvenido a tu ticket.\n\n{EMOJI_FIRE} **El equipo de soporte te atenderá pronto.**",
                color=discord.Color(int(config["color"], 16))
            )
            embed_ticket.add_field(
                name=f"{EMOJI_NOTES} Instrucciones",
                value="• Explica tu problema con detalle\n• Sé paciente, el staff responderá pronto\n• Usa los botones de abajo para gestionar el ticket",
                inline=False
            )
            embed_ticket.set_footer(text="Sistema de Tickets • Dragons")
            embed_ticket.timestamp = datetime.datetime.utcnow()
            
            # Botones de control del ticket
            view_controls = TicketControls()
            
            await canal_ticket.send(f"{interaction.user.mention} {rol_soporte.mention}", embed=embed_ticket, view=view_controls)
            
            # Log en canal de logs
            canal_logs = interaction.guild.get_channel(int(config["canal_logs_id"]))
            if canal_logs:
                embed_log = discord.Embed(
                    title=f"{EMOJI_TICKET} Nuevo Ticket Creado",
                    description=f"**Usuario:** {interaction.user.mention}\n**Canal:** {canal_ticket.mention}\n**Ticket:** #{ticket_number}",
                    color=discord.Color.green()
                )
                embed_log.timestamp = datetime.datetime.utcnow()
                await canal_logs.send(embed=embed_log)
            
            await interaction.response.send_message(
                f"✅ Tu ticket ha sido creado: {canal_ticket.mention}",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error al crear ticket: {e}", ephemeral=True)


# ==============================
# BOTONES DE CONTROL DEL TICKET
# ==============================
class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.red, emoji="❌", custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild.id)
        canal_id = str(interaction.channel.id)
        
        try:
            # Verificar que el ticket existe
            ticket_data = supabase.table("tickets").select("*").eq("canal_id", canal_id).execute()
            
            if not ticket_data.data:
                await interaction.response.send_message("❌ No se encontró este ticket.", ephemeral=True)
                return
            
            ticket = ticket_data.data[0]
            config_data = supabase.table("ticket_config").select("*").eq("guild_id", guild_id).execute()
            
            # Crear transcript (resumen del chat)
            messages = []
            async for msg in interaction.channel.history(limit=100, oldest_first=True):
                messages.append(f"[{msg.created_at.strftime('%Y-%m-%d %H:%M')}] {msg.author.name}: {msg.content}")
            
            transcript = "\n".join(messages)
            
            # Actualizar estado en BD
            supabase.table("tickets").update({
                "estado": "cerrado",
                "cerrado_por": str(interaction.user.id),
                "cerrado_at": datetime.datetime.utcnow().isoformat()
            }).eq("canal_id", canal_id).execute()
            
            # Enviar log
            if config_data.data:
                canal_logs = interaction.guild.get_channel(int(config_data.data[0]["canal_logs_id"]))
                if canal_logs:
                    embed_log = discord.Embed(
                        title=f"{EMOJI_CLOSE} Ticket Cerrado",
                        description=(
                            f"**Ticket:** #{ticket['numero']}\n"
                            f"**Usuario:** <@{ticket['user_id']}>\n"
                            f"**Cerrado por:** {interaction.user.mention}\n"
                            f"**Canal:** {interaction.channel.mention}"
                        ),
                        color=discord.Color.red()
                    )
                    embed_log.timestamp = datetime.datetime.utcnow()
                    await canal_logs.send(embed=embed_log)
            
            await interaction.response.send_message(f"{EMOJI_CLOSE} Cerrando ticket en 5 segundos...")
            await asyncio.sleep(5)
            await interaction.channel.delete()
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error al cerrar ticket: {e}", ephemeral=True)


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
        total_tickets = len(supabase.table("tickets").select("id").execute().data)

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
        embed.add_field(name=f"{EMOJI_TICKET}  Tickets Totales", value=f"**{total_tickets}**", inline=True)
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
    import asyncio

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
# COMANDO /UNMUTE (solo administradores)
# ==============================

@bot.tree.command(name="unmute", description="Quita el silencio de un usuario (solo administradores).")
@app_commands.describe(
    usuario="Usuario al que se le quitará el silencio",
    motivo="Motivo para quitar el mute"
)
@app_commands.checks.has_permissions(administrator=True)
async def unmute(interaction: discord.Interaction, usuario: discord.Member, motivo: str = "No especificado"):

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
                title=f" {EMOJI_DRAGON} Se te ha quitado el silencio",
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
# COMANDO /userinfo (público)
# ==============================

@bot.tree.command(name="userinfo", description="Muestra tu perfil o el de otro usuario.")
@app_commands.describe(usuario="Usuario a consultar (opcional)")
async def perfil(interaction: discord.Interaction, usuario: discord.Member = None):

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
# COMANDO /HELP (Lista de comandos del bot)
# ==============================
@bot.tree.command(name="help", description="📖 Muestra todos los comandos disponibles del sistema Dragons.")
async def help_command(interaction: discord.Interaction):
    try:
        embed = discord.Embed(
            title=f"{EMOJI_DRAGON} **[ DV ] Dragons Command Center** {EMOJI_DRAGON}",
            description=(
                f"{EMOJI_FIRE} **Bienvenido al sistema de ayuda Dragons**\n"
                f"Aquí encontrarás todos los comandos disponibles agrupados por categoría.\n\n"
                f"**Usa los comandos con** `/nombre_comando`\n"
            ),
            color=discord.Color.blue()
        )

        # 🧭 Categoría: Bienvenida
        embed.add_field(
            name=f"{EMOJI_WELCOME} **Bienvenida**",
            value=(
                f"`/crear-bienvenida` → Configura el mensaje de bienvenida personalizado.\n"
                f"`on_member_join` → Envía automáticamente la bienvenida al nuevo usuario."
            ),
            inline=False
        )

        # 🎫 Sistema de Tickets
        embed.add_field(
            name=f"{EMOJI_TICKET} **Sistema de Tickets**",
            value=(
                f"`/ticket-config` → Configura el sistema de tickets (categoría, logs, rol soporte).\n"
                f"`/ticket-panel` → Crea el panel de tickets en el canal actual.\n"
                f"**Botones:** Crear, Cerrar tickets desde el panel interactivo."
            ),
            inline=False
        )

        # ⚔️ Moderación
        embed.add_field(
            name=f"{EMOJI_MOD} **Moderación**",
            value=(
                f"`/ban` → Banea un usuario del servidor.\n"
                f"`/unban` → Desbanea un usuario.\n"
                f"`/mute` → Silencia temporalmente a un usuario.\n"
                f"`/unmute` → Quita el silencio a un usuario."
            ),
            inline=False
        )

        # ⚠️ Advertencias
        embed.add_field(
            name=f"{EMOJI_ALERT} **Advertencias (Warns)**",
            value=(
                f"`/warn` → Advierte a un usuario.\n"
                f"`/warnings` → Muestra las advertencias de un usuario.\n"
                f"`/unwarns` → Elimina una o todas las advertencias de un usuario."
            ),
            inline=False
        )

        # 📊 Estadísticas y Perfil
        embed.add_field(
            name=f"{EMOJI_BOT} **Estadísticas y Perfil**",
            value=(
                f"`/botstatistics` → Muestra estadísticas globales del bot.\n"
                f"`/userinfo` → Muestra el perfil de un usuario."
            ),
            inline=False
        )

        # 🔰 Sistema
        embed.add_field(
            name=f"{EMOJI_DERECHA} **Sistema y soporte**",
            value=(
                f"`/help` → Muestra este menú de ayuda.\n"
                f"**Tiempo activo:** El bot lleva funcionando desde su última activación."
            ),
            inline=False
        )

        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1432855339732177067.webp")
        embed.set_footer(
            text="🐲 Dragons Development • Centro de Comandos",
            icon_url="https://cdn.discordapp.com/emojis/1432855375165526036.webp"
        )
        embed.timestamp = datetime.datetime.utcnow()

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error al mostrar la ayuda: {e}", ephemeral=True)

# ==============================
# COMANDO /TICKETS (TODO EN UNO)
# ==============================
@bot.tree.command(name="tickets", description="🎫 Configura y crea el sistema de tickets completo")
@app_commands.describe(
    categoria="Categoría donde se crearán los tickets",
    canal_logs="Canal donde se registrarán los logs",
    rol_soporte="Rol que podrá ver los tickets",
    canal_panel="Canal donde se enviará el panel",
    titulo="Título del panel",
    descripcion="Descripción del panel",
    color="Color del embed (hex, ej: 4169e1)",
    cantidad_botones="Cantidad de botones (1-7)"
)
@app_commands.checks.has_permissions(administrator=True)
async def tickets_todo(
    interaction: discord.Interaction,
    categoria: discord.CategoryChannel,
    canal_logs: discord.TextChannel,
    rol_soporte: discord.Role,
    canal_panel: discord.TextChannel,
    titulo: str = "🎫 Sistema de Tickets",
    descripcion: str = "Selecciona el tipo de ayuda que necesitas",
    color: str = "4169e1",
    cantidad_botones: int = 1
):
    # Validaciones
    if cantidad_botones < 1 or cantidad_botones > 7:
        await interaction.response.send_message("❌ La cantidad debe estar entre 1 y 7.", ephemeral=True)
        return
    
    color_limpio = color.lstrip('#')
    if len(color_limpio) != 6 or not all(c in '0123456789abcdefABCDEF' for c in color_limpio):
        await interaction.response.send_message("❌ Color inválido. Usa formato hex (ej: 4169e1)", ephemeral=True)
        return
    
    guild_id = str(interaction.guild.id)
    
    try:
        # Guardar configuración base
        supabase.table("ticket_config").upsert({
            "guild_id": guild_id,
            "categoria_id": str(categoria.id),
            "canal_logs_id": str(canal_logs.id),
            "rol_soporte_id": str(rol_soporte.id),
            "titulo": titulo,
            "descripcion": descripcion,
            "color": color_limpio,
            "canal_panel_id": str(canal_panel.id)
        }).execute()
        
        # Eliminar botones antiguos
        supabase.table("ticket_botones").delete().eq("guild_id", guild_id).execute()
        
        await interaction.response.defer(ephemeral=True)
        
        # Configurar cada botón mediante mensajes
        botones_config = []
        
        for i in range(1, cantidad_botones + 1):
            embed_config = discord.Embed(
                title=f"⚙️ Configurar Botón {i}/{cantidad_botones}",
                description=(
                    "Responde con el formato:\n"
                    "```\n"
                    "Nombre: Soporte Técnico\n"
                    "Emoji: 🛠️\n"
                    "Color: green\n"
                    "Categoría: Soporte\n"
                    "```\n"
                    "**Colores disponibles:** green, red, blue, grey, blurple"
                ),
                color=discord.Color(int(color_limpio, 16))
            )
            
            await interaction.followup.send(embed=embed_config, ephemeral=True)
            
            def check(m):
                return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
            
            try:
                msg = await bot.wait_for('message', timeout=60.0, check=check)
                
                # Parsear respuesta
                lineas = msg.content.strip().split('\n')
                config_boton = {}
                
                for linea in lineas:
                    if ':' in linea:
                        clave, valor = linea.split(':', 1)
                        clave = clave.strip().lower()
                        valor = valor.strip()
                        
                        if 'nombre' in clave:
                            config_boton['nombre'] = valor
                        elif 'emoji' in clave:
                            config_boton['emoji'] = valor
                        elif 'color' in clave:
                            config_boton['color'] = valor.lower()
                        elif 'categor' in clave:
                            config_boton['categoria'] = valor
                
                # Validar
                if len(config_boton) < 4:
                    await interaction.followup.send("❌ Faltan datos. Cancelando configuración.", ephemeral=True)
                    return
                
                botones_config.append(config_boton)
                
                # Guardar en BD
                supabase.table("ticket_botones").insert({
                    "guild_id": guild_id,
                    "nombre": config_boton['nombre'],
                    "emoji": config_boton['emoji'],
                    "color": config_boton['color'],
                    "categoria": config_boton['categoria'],
                    "orden": i
                }).execute()
                
                await msg.delete()
                await interaction.followup.send(f"✅ Botón {i} configurado: {config_boton['nombre']}", ephemeral=True)
                
            except asyncio.TimeoutError:
                await interaction.followup.send("⏱️ Tiempo agotado. Cancelando configuración.", ephemeral=True)
                return
        
        # Crear el panel
        embed_panel = discord.Embed(
            title=titulo,
            description=descripcion,
            color=discord.Color(int(color_limpio, 16))
        )
        embed_panel.add_field(
            name=f"{EMOJI_FIRE} ¿Necesitas ayuda?",
            value="Selecciona el tipo de ticket usando los botones de abajo.",
            inline=False
        )
        embed_panel.set_thumbnail(url="https://cdn.discordapp.com/emojis/1432855339732177067.webp")
        embed_panel.set_footer(text="Sistema de Tickets • Dragons")
        embed_panel.timestamp = datetime.datetime.utcnow()
        
        # Crear vista con botones
        view = TicketPanelView(botones_config)
        
        await canal_panel.send(embed=embed_panel, view=view)
        
        embed_final = discord.Embed(
            title="✅ Sistema de Tickets Configurado",
            description=(
                f"**Categoría:** {categoria.mention}\n"
                f"**Canal Logs:** {canal_logs.mention}\n"
                f"**Rol Soporte:** {rol_soporte.mention}\n"
                f"**Panel en:** {canal_panel.mention}\n"
                f"**Botones:** {cantidad_botones}"
            ),
            color=discord.Color.green()
        )
        
        await interaction.followup.send(embed=embed_final, ephemeral=True)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# ==============================
# VISTA DEL PANEL (DINÁMICA)
# ==============================
class TicketPanelView(discord.ui.View):
    def __init__(self, botones_config: list):
        super().__init__(timeout=None)
        
        colores_map = {
            "green": discord.ButtonStyle.green,
            "red": discord.ButtonStyle.red,
            "blue": discord.ButtonStyle.primary,
            "blurple": discord.ButtonStyle.primary,
            "grey": discord.ButtonStyle.secondary,
            "gray": discord.ButtonStyle.secondary
        }
        
        for idx, boton_data in enumerate(botones_config):
            button = discord.ui.Button(
                label=boton_data["nombre"],
                style=colores_map.get(boton_data["color"], discord.ButtonStyle.green),
                emoji=boton_data["emoji"],
                custom_id=f"create_ticket_{idx}_{boton_data['categoria']}"
            )
            button.callback = self.crear_callback_ticket(boton_data)
            self.add_item(button)
    
    def crear_callback_ticket(self, boton_data):
        async def callback(interaction: discord.Interaction):
            guild_id = str(interaction.guild.id)
            user_id = str(interaction.user.id)
            
            try:
                # Verificar ticket existente
                existing = supabase.table("tickets").select("*").eq("guild_id", guild_id).eq("user_id", user_id).eq("estado", "abierto").execute()
                
                if existing.data:
                    await interaction.response.send_message(
                        f"❌ Ya tienes un ticket abierto: <#{existing.data[0]['canal_id']}>",
                        ephemeral=True
                    )
                    return
                
                # Obtener config
                config = supabase.table("ticket_config").select("*").eq("guild_id", guild_id).execute()
                
                if not config.data:
                    await interaction.response.send_message("❌ Sistema no configurado.", ephemeral=True)
                    return
                
                cfg = config.data[0]
                categoria = interaction.guild.get_channel(int(cfg["categoria_id"]))
                rol_soporte = interaction.guild.get_role(int(cfg["rol_soporte_id"]))
                
                # Crear canal
                overwrites = {
                    interaction.guild.default_role: PermissionOverwrite(view_channel=False),
                    interaction.user: PermissionOverwrite(view_channel=True, send_messages=True),
                    rol_soporte: PermissionOverwrite(view_channel=True, send_messages=True),
                    interaction.guild.me: PermissionOverwrite(view_channel=True, manage_channels=True)
                }
                
                ticket_num = len(supabase.table("tickets").select("id").eq("guild_id", guild_id).execute().data) + 1
                
                canal = await categoria.create_text_channel(
                    name=f"ticket-{ticket_num}-{interaction.user.name}",
                    overwrites=overwrites
                )
                
                # Guardar en BD
                supabase.table("tickets").insert({
                    "guild_id": guild_id,
                    "user_id": user_id,
                    "canal_id": str(canal.id),
                    "numero": ticket_num,
                    "tipo": boton_data["categoria"],
                    "estado": "abierto"
                }).execute()
                
                # Embed del ticket
                embed = discord.Embed(
                    title=f"{boton_data['emoji']} {boton_data['categoria']} - Ticket #{ticket_num}",
                    description=f"Hola {interaction.user.mention}, bienvenido a tu ticket.\n\n{EMOJI_FIRE} El equipo te atenderá pronto.",
                    color=discord.Color(int(cfg["color"], 16))
                )
                embed.add_field(
                    name=f"{EMOJI_NOTES} Instrucciones",
                    value="• Explica tu problema con detalle\n• Sé paciente\n• Usa el botón para cerrar",
                    inline=False
                )
                embed.timestamp = datetime.datetime.utcnow()
                
                view_controls = TicketControls()
                await canal.send(f"{interaction.user.mention} {rol_soporte.mention}", embed=embed, view=view_controls)
                
                # Log
                canal_logs = interaction.guild.get_channel(int(cfg["canal_logs_id"]))
                if canal_logs:
                    log_embed = discord.Embed(
                        title=f"{EMOJI_TICKET} Ticket Creado",
                        description=f"**Usuario:** {interaction.user.mention}\n**Tipo:** {boton_data['categoria']}\n**Canal:** {canal.mention}",
                        color=discord.Color.green()
                    )
                    await canal_logs.send(embed=log_embed)
                
                await interaction.response.send_message(f"✅ Ticket creado: {canal.mention}", ephemeral=True)
                
            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
        
        return callback


# ==============================
# CONTROLES DEL TICKET
# ==============================
class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.red, emoji="❌", custom_id="close_ticket_final")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        canal_id = str(interaction.channel.id)
        
        try:
            ticket = supabase.table("tickets").select("*").eq("canal_id", canal_id).execute()
            
            if not ticket.data:
                await interaction.response.send_message("❌ Ticket no encontrado.", ephemeral=True)
                return
            
            supabase.table("tickets").update({
                "estado": "cerrado",
                "cerrado_por": str(interaction.user.id),
                "cerrado_at": datetime.datetime.utcnow().isoformat()
            }).eq("canal_id", canal_id).execute()
            
            await interaction.response.send_message(f"{EMOJI_CLOSE} Cerrando ticket en 5 segundos...")
            await asyncio.sleep(5)
            await interaction.channel.delete()
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
            
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