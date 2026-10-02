import discord
from discord import app_commands
import os

# IDs de configuración
ROL_ALTO_MANDO = 1549479823200747521

# Memoria temporal para guardar las apelaciones pendientes
apelaciones_db = []

class ApelacionModal(discord.ui.Modal, title="Formulario de Apelación"):
    razon = discord.ui.TextInput(
        label="¿Por qué deberíamos aceptar tu apelación?",
        style=discord.TextStyle.paragraph,
        placeholder="Explica detalladamente tu caso...",
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Guardar en la base de datos temporal
        apelacion_data = {
            "usuario": str(interaction.user),
            "id_usuario": interaction.user.id,
            "razon": self.razon.value
        }
        apelaciones_db.append(apelacion_data)

        # Buscar si existe el canal exclusivo para Alto Mando o crearlo/notificar
        guild = interaction.guild
        canal_nombre = "apelaciones-staff"
        canal = discord.utils.get(guild.text_channels, name=canal_nombre)

        if not canal:
            # Crear canal protegido si no existe
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.get_role(ROL_ALTO_MANDO): discord.PermissionOverwrite(read_messages=True, send_messages=True) if guild.get_role(ROL_ALTO_MANDO) else discord.PermissionOverwrite(read_messages=True)
            }
            try:
                canal = await guild.create_text_channel(canal_nombre, overwrites=overwrites, topic="Canal exclusivo para revisión de apelaciones por el Alto Mando.")
            except Exception:
                canal = None

        # Enviar aviso al canal protegido
        if canal:
            embed_aviso = discord.Embed(
                title="📥 ¡Nueva Apelación Recibida!",
                description=f"**Usuario:** {interaction.user.mention} (`{interaction.user.id}`)\n\n**Motivo:**\n{self.razon.value}",
                color=discord.Color.orange()
            )
            await canal.send(content=f"<@&{ROL_ALTO_MANDO}>", embed=embed_aviso)

        await interaction.response.send_message("✅ ¡Tu apelación ha sido enviada exitosamente al Alto Mando para su revisión!", ephemeral=True)


class VistaApelacionBotones(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Apelar Sanción", style=discord.ButtonStyle.primary, custom_id="btn_apelar")
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

# Comando 1: Postulación General
@client.tree.command(name="postulacion", description="Envía el formulario de postulación para el staff de Hakkuze")
async def postulacion(interaction: discord.Interaction):
    formulario = (
        "🛡️ **POSTULACIÓN STAFF — HAKKUZE**\n\n"
        "👤 **INFORMACIÓN**\n\n"
        "**1. Nombre / Apodo:**\nRespuesta:\n\n"
        "**2. Edad:**\nRespuesta:\n\n"
        "**3. País / Zona horaria:**\nRespuesta:\n\n"
        "**4. ¿Cuánto tiempo llevas en Hakkuze?**\nRespuesta:\n\n"
        "🎯 **EXPERIENCIA**\n\n"
        "**5. ¿Has sido Staff anteriormente?**\nSí / No\nSi es así, cuéntanos brevemente tu experiencia.\n\n"
        "**6. ¿Qué experiencia tienes moderando servidores de Discord?**\nRespuesta:\n\n"
        "**7. ¿Qué bots o herramientas de Discord sabes utilizar?**\nRespuesta:\n\n"
        "🧠 **SITUACIONES**\n\n"
        "**8. Un usuario está incumpliendo las normas constantemente. ¿Qué harías?**\nRespuesta:\n\n"
        "**9. Un amigo tuyo rompe una regla. ¿Lo sancionarías? ¿Por qué?**\nRespuesta:\n\n"
        "**10. ¿Qué harías si ves a otro Staff abusando de sus permisos?**\nRespuesta:\n\n"
        "💎 **MOTIVACIÓN**\n\n"
        "**11. ¿Por qué quieres ser Staff de Hakkuze?**\nRespuesta:\n\n"
        "**12. ¿Qué podrías aportar al servidor?**\nRespuesta:\n\n"
        "**13. ¿Qué área te interesa?**\nModeración / Soporte / Eventos / Alianzas / Otra\n\n"
        "**14. ¿Cuánto tiempo podrías dedicar diariamente al servidor?**\nRespuesta:\n\n"
        "**15. ¿Por qué deberíamos elegirte?**\nRespuesta:"
    )
    await interaction.response.send_message(formulario)

# Comando 2: Postulación Caza Alianzas
@client.tree.command(name="caza_alianzas", description="Envía el formulario para postularse a Caza Alianzas en Hakkuze")
async def caza_alianzas(interaction: discord.Interaction):
    form_alianzas = (
        "🤝 **POSTULACIÓN | CAZA ALIANZAS — HAKKUZE**\n\n"
        "**1. 👤 Usuario de Discord:**\nRespuesta:\n\n"
        "**2. 🎂 Edad:**\nRespuesta:\n\n"
        "**3. 💼 ¿Has trabajado haciendo alianzas anteriormente?**\nRespuesta:\n\n"
        "**4. 📊 ¿Cuántas alianzas crees que podrías conseguir semanalmente?**\nRespuesta:\n\n"
        "**5. 🗣️ ¿Por qué quieres formar parte del equipo de Caza Alianzas?**\nRespuesta:\n\n"
        "**6. ⏱️ ¿Cuánto tiempo puedes dedicar diariamente?**\nRespuesta:\n\n"
        "**7. 💬 ¿Tienes experiencia hablando con otros Staffs?**\nRespuesta:\n\n"
        "**8. 📝 ¿Por qué deberíamos aceptarte?**\nRespuesta:\n\n"
        "🔒 *La información será revisada exclusivamente por el Staff de Hakkuze.*"
    )
    await interaction.response.send_message(form_alianzas)

# Comando 3: Panel de Apelaciones con Botón interactivo
@client.tree.command(name="panel_apelaciones", description="Crea el panel interactivo para que los usuarios puedan apelar")
@app_commands.checks.has_permissions(administrator=True)
async def panel_apelaciones(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚖️ Sistema de Apelaciones - Hakkuze",
        description="Si fuiste sancionado y deseas apelar, haz clic en el botón de abajo para rellenar tu formulario.",
        color=discord.Color.blue()
    )
    await interaction.channel.send(embed=embed, view=VistaApelacionBotones())
    await interaction.response.send_message("✅ ¡Panel de apelaciones creado con éxito!", ephemeral=True)

# Comando 4: Crear Embed Personalizado con hasta 2 botones opcionales
@client.tree.command(name="crear_embed", description="Personaliza y envía un embed con hasta 2 botones opcionales")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    titulo="Título del Embed",
    descripcion="Contenido del Embed",
    color="Color en HEX (ejemplo: #00ff00)",
    btn1_texto="Texto del Botón 1 (Opcional)",
    btn1_url="Enlace URL del Botón 1 (Opcional)",
    btn2_texto="Texto del Botón 2 (Opcional)",
    btn2_url="Enlace URL del Botón 2 (Opcional)"
)
async def crear_embed(
    interaction: discord.Interaction, 
    titulo: str, 
    descripcion: str, 
    color: str = "#3498db", 
    btn1_texto: str = None, 
    btn1_url: str = None, 
    btn2_texto: str = None, 
    btn2_url: str = None
):
    try:
        color_limpio = int(color.replace("#", ""), 16)
    except ValueError:
        color_limpio = 0x3498db

    embed = discord.Embed(title=titulo, description=descripcion, color=color_limpio)
    
    view = discord.ui.View()
    if btn1_texto and btn1_url:
        view.add_item(discord.ui.Button(label=btn1_texto, url=btn1_url))
    if btn2_texto and btn2_url:
        view.add_item(discord.ui.Button(label=btn2_texto, url=btn2_url))

    if len(view.children) > 0:
        await interaction.channel.send(embed=embed, view=view)
    else:
        await interaction.channel.send(embed=embed)
        
    await interaction.response.send_message("✅ ¡Embed enviado correctamente!", ephemeral=True)

# Comando 5: Ver apelaciones pendientes (Exclusivo o filtrado para Alto Mando)
@client.tree.command(name="apelaciones_pendientes", description="Muestra la lista de apelaciones pendientes")
async def apelaciones_pendientes(interaction: discord.Interaction):
    # Verificar si el usuario tiene el rol de Alto Mando o es Administrador
    tiene_rol = any(role.id == ROL_ALTO_MANDO for role in interaction.user.roles)
    if not tiene_rol and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ No tienes permisos para usar este comando (requiere el rol de Alto Mando).", ephemeral=True)
        return

    if not apelaciones_db:
        await interaction.response.send_message("📂 No hay apelaciones pendientes registradas en este momento.", ephemeral=True)
        return

    embed = discord.Embed(title="📋 Apelaciones Pendientes", color=discord.Color.yellow())
    for i, ap in enumerate(apelaciones_db[:10], 1): # Muestra máximo las últimas 10
        embed.add_field(
            name=f"#{i} - Usuario: {ap['usuario']}",
            value=f"**ID:** `{ap['id_usuario']}`\n**Razón:** {ap['razon'][:200]}...",
            inline=False
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)

client.run(os.environ['DISCORD_TOKEN'])
