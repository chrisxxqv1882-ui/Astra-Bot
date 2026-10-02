import discord
from discord import app_commands
import os

# IDs de configuración
ROL_ALTO_MANDO = 1549479823200747521

# Memoria temporal para guardar las apelaciones pendientes y configuraciones de embeds
apelaciones_db = []
config_apelacion_embed = {
    "titulo": "⚖️ Sistema de Apelaciones - Hakkuze",
    "descripcion": "Si fuiste sancionado y deseas apelar, haz clic en el botón de abajo para rellenar tu formulario y enviarlo al Alto Mando.",
    "color": 0x3498db,
    "autor": "Hakkuze - Moderación",
    "thumbnail": None,
    "image": None,
    "footer": "Sistema seguro de apelaciones",
    "ticket_titulo": "📥 ¡Nueva Apelación Recibida!",
    "ticket_descripcion": "El usuario {usuario} ha enviado una apelación.\n\n**Motivo:**\n{razon}"
}

# Modal para el formulario de Apelación
class ApelacionModal(discord.ui.Modal, title="Formulario de Apelación"):
    razon = discord.ui.TextInput(
        label="¿Por qué deberíamos aceptar tu apelación?",
        style=discord.TextStyle.paragraph,
        placeholder="Explica detalladamente tu caso...",
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        apelacion_data = {
            "usuario": str(interaction.user),
            "id_usuario": interaction.user.id,
            "razon": self.razon.value
        }
        apelaciones_db.append(apelacion_data)

        guild = interaction.guild
        canal_nombre = "apelaciones-staff"
        canal = discord.utils.get(guild.text_channels, name=canal_nombre)

        if not canal:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.get_role(ROL_ALTO_MANDO): discord.PermissionOverwrite(read_messages=True, send_messages=True) if guild.get_role(ROL_ALTO_MANDO) else discord.PermissionOverwrite(read_messages=True)
            }
            try:
                canal = await guild.create_text_channel(canal_nombre, overwrites=overwrites, topic="Canal exclusivo para revisión de apelaciones por el Alto Mando.")
            except Exception:
                canal = None

        if canal:
            # Usar la configuración personalizada del ticket
            desc_formateada = config_apelacion_embed["ticket_descripcion"].format(
                usuario=interaction.user.mention,
                razon=self.razon.value
            )
            embed_aviso = discord.Embed(
                title=config_apelacion_embed["ticket_titulo"],
                description=desc_formateada,
                color=config_apelacion_embed["color"]
            )
            await canal.send(content=f"<@&{ROL_ALTO_MANDO}>", embed=embed_aviso)

        await interaction.response.send_message("✅ ¡Tu apelación ha sido enviada exitosamente al Alto Mando para su revisión!", ephemeral=True)

# Vistas de Botones
class VistaPostulaciones(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🛡️ Postulación Staff", style=discord.ButtonStyle.primary, custom_id="btn_staff")
    async def btn_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        formulario = (
            "🛡️ **POSTULACIÓN STAFF — HAKKUZE**\n\n"
            "👤 **INFORMACIÓN**\n\n"
            "**1. Nombre / Apodo:**\nRespuesta:\n\n"
            "**2. Edad:**\nRespuesta:\n\n"
            "**3. País / Zona horaria:**\nRespuesta:\n\n"
            "**4. ¿Cuánto tiempo llevas en Hakkuze?**\nRespuesta:\n\n"
            "🎯 **EXPERIENCIA**\n\n"
            "**5. ¿Has sido Staff anteriormente?**\nSí / No\n\n"
            "**6. ¿Qué experiencia tienes moderando servidores?**\nRespuesta:\n\n"
            "💎 **MOTIVACIÓN**\n\n"
            "**7. ¿Por qué quieres ser Staff de Hakkuze?**\nRespuesta:\n\n"
            "**8. ¿Cuánto tiempo puedes dedicar diariamente?**\nRespuesta:"
        )
        await interaction.response.send_message(formulario, ephemeral=True)

    @discord.ui.button(label="🤝 Caza Alianzas", style=discord.ButtonStyle.success, custom_id="btn_alianzas")
    async def btn_alianzas(self, interaction: discord.Interaction, button: discord.ui.Button):
        form_alianzas = (
            "🤝 **POSTULACIÓN | CAZA ALIANZAS — HAKKUZE**\n\n"
            "**1. 👤 Usuario de Discord:**\nRespuesta:\n\n"
            "**2. 🎂 Edad:**\nRespuesta:\n\n"
            "**3. 💼 ¿Has trabajado haciendo alianzas anteriormente?**\nRespuesta:\n\n"
            "**4. 📊 ¿Cuántas alianzas podrías conseguir semanalmente?**\nRespuesta:\n\n"
            "**5. 🗣️ ¿Por qué quieres formar parte del equipo?**\nRespuesta:\n\n"
            "🔒 *La información será revisada exclusivamente por el Staff.*"
        )
        await interaction.response.send_message(form_alianzas, ephemeral=True)

class VistaApelacionBotones(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Apelar Sanción", style=discord.ButtonStyle.danger, custom_id="btn_apelar")
    async def boton_apelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ApelacionModal())


class Bot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("¡Slash commands sincronizados!")

client = Bot()

@client.event
async def on_ready():
    print(f'¡Bot conectado con éxito como {client.user}!')

# Comando individual: Postulación General
@client.tree.command(name="postulacion", description="Envía el formulario de postulación para el staff")
async def postulacion(interaction: discord.Interaction):
    formulario = "🛡️ **POSTULACIÓN STAFF — HAKKUZE**\nCopia y responde este formato..."
    await interaction.response.send_message(formulario)

# Comando individual: Caza Alianzas
@client.tree.command(name="caza_alianzas", description="Envía el formulario para Caza Alianzas")
async def caza_alianzas(interaction: discord.Interaction):
    form_alianzas = "🤝 **POSTULACIÓN | CAZA ALIANZAS — HAKKUZE**\nCopia y responde este formato..."
    await interaction.response.send_message(form_alianzas)

# COMANDO CONFIG: Muestra el panel con todas las postulaciones disponibles mediante botones
@client.tree.command(name="config", description="Envía el panel central de postulaciones de Hakkuze")
@app_commands.checks.has_permissions(administrator=True)
async def config_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📋 Centro de Postulaciones - Hakkuze",
        description="Selecciona el botón correspondiente al formulario en el que deseas postularte:",
        color=discord.Color.purple()
    )
    embed.set_footer(text="Hakkuze Official • Sistema de Reclutamiento")
    await interaction.channel.send(embed=embed, view=VistaPostulaciones())
    await interaction.response.send_message("✅ ¡Panel de configuraciones/postulaciones enviado con éxito!", ephemeral=True)

# COMANDO PARA CREAR EL PANEL DE APELACIONES PERSONALIZADO
@client.tree.command(name="panel_apelaciones", description="Envía el panel de apelaciones configurado")
@app_commands.checks.has_permissions(administrator=True)
async def panel_apelaciones(interaction: discord.Interaction):
    embed = discord.Embed(
        title=config_apelacion_embed["titulo"],
        description=config_apelacion_embed["descripcion"],
        color=config_apelacion_embed["color"]
    )
    if config_apelacion_embed["autor"]:
        embed.set_author(name=config_apelacion_embed["autor"])
    if config_apelacion_embed["thumbnail"]:
        embed.set_thumbnail(url=config_apelacion_embed["thumbnail"])
    if config_apelacion_embed["image"]:
        embed.set_image(url=config_apelacion_embed["image"])
    if config_apelacion_embed["footer"]:
        embed.set_footer(text=config_apelacion_embed["footer"])

    await interaction.channel.send(embed=embed, view=VistaApelacionBotones())
    await interaction.response.send_message("✅ ¡Panel de apelaciones desplegado!", ephemeral=True)

# COMANDO PARA CONFIGURAR TODOS LOS DETALLES DEL EMBED DE APELACIÓN Y SU TICKET
@client.tree.command(name="configurar_apelaciones", description="Personaliza los embeds del sistema de apelaciones y tickets")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    titulo="Título del embed principal",
    descripcion="Descripción del embed principal",
    color="Color en HEX (ej: #3498db)",
    autor="Texto del autor (opcional)",
    thumbnail="URL de la imagen pequeña/thumbnail (opcional)",
    imagen="URL de la imagen grande central (opcional)",
    footer="Texto del pie de página (opcional)",
    ticket_titulo="Título del embed que llega al canal del ticket",
    ticket_descripcion="Descripción del ticket (Usa {usuario} y {razon})"
)
async def configurar_apelaciones(
    interaction: discord.Interaction,
    titulo: str = None,
    descripcion: str = None,
    color: str = None,
    autor: str = None,
    thumbnail: str = None,
    imagen: str = None,
    footer: str = None,
    ticket_titulo: str = None,
    ticket_descripcion: str = None
):
    if titulo: config_apelacion_embed["titulo"] = titulo
    if descripcion: config_apelacion_embed["descripcion"] = descripcion
    if color:
        try: config_apelacion_embed["color"] = int(color.replace("#", ""), 16)
        except: pass
    if autor is not None: config_apelacion_embed["autor"] = autor if autor.lower() != "none" else None
    if thumbnail is not None: config_apelacion_embed["thumbnail"] = thumbnail if thumbnail.lower() != "none" else None
    if imagen is not None: config_apelacion_embed["image"] = imagen if imagen.lower() != "none" else None
    if footer is not None: config_apelacion_embed["footer"] = footer if footer.lower() != "none" else None
    if ticket_titulo: config_apelacion_embed["ticket_titulo"] = ticket_titulo
    if ticket_descripcion: config_apelacion_embed["ticket_descripcion"] = ticket_descripcion

    await interaction.response.send_message("✅ ¡Configuración de apelaciones y tickets actualizada con éxito! Usa `/panel_apelaciones` para ver los cambios.", ephemeral=True)

# Comando: Ver apelaciones pendientes (Solo Alto Mando)
@client.tree.command(name="apelaciones_pendientes", description="Muestra la lista de apelaciones pendientes")
async def apelaciones_pendientes(interaction: discord.Interaction):
    tiene_rol = any(role.id == ROL_ALTO_MANDO for role in interaction.user.roles)
    if not tiene_rol and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ No tienes permisos para usar este comando (requiere el rol de Alto Mando).", ephemeral=True)
        return

    if not apelaciones_db:
        await interaction.response.send_message("📂 No hay apelaciones pendientes registradas.", ephemeral=True)
        return

    embed = discord.Embed(title="📋 Apelaciones Pendientes", color=discord.Color.yellow())
    for i, ap in enumerate(apelaciones_db[:10], 1):
        embed.add_field(
            name=f"#{i} - Usuario: {ap['usuario']}",
            value=f"**ID:** `{ap['id_usuario']}`\n**Razón:** {ap['razon'][:200]}...",
            inline=False
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)

client.run(os.environ['DISCORD_TOKEN'])