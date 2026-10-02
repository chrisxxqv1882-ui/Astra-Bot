import discord
from discord.ext import commands
import os

# IDs de configuración
ROL_ALTO_MANDO = 1549479823200747521

# Memoria temporal
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

# Configuración del bot con el prefijo a¡
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="a¡", intents=intents)

@bot.event
async def on_ready():
    print(f'¡Bot conectado con éxito como {bot.user}!')

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

class VistaPostulaciones(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🛡️ Postulación Staff", style=discord.ButtonStyle.primary, custom_id="btn_staff")
    async def btn_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        formulario = (
            "🛡️️ **POSTULACIÓN STAFF — HAKKUZE**\n\n"
            "👤 **INFORMACIÓN**\n"
            "**1. Nombre / Apodo:**\n**2. Edad:**\n**3. País / Zona horaria:**\n**4. ¿Cuánto tiempo llevas en Hakkuze?**\n\n"
            "🎯 **EXPERIENCIA**\n"
            "**5. ¿Has sido Staff anteriormente?**\n**6. ¿Qué experiencia tienes moderando?**\n\n"
            "💎 **MOTIVACIÓN**\n"
            "**7. ¿Por qué quieres ser Staff?**\n**8. ¿Cuánto tiempo puedes dedicar?**"
        )
        await interaction.response.send_message(formulario, ephemeral=True)

    @discord.ui.button(label="🤝 Caza Alianzas", style=discord.ButtonStyle.success, custom_id="btn_alianzas")
    async def btn_alianzas(self, interaction: discord.Interaction, button: discord.ui.Button):
        form_alianzas = (
            "🤝 **POSTULACIÓN | CAZA ALIANZAS — HAKKUZE**\n\n"
            "**1. 👤 Usuario de Discord:**\n**2. 🎂 Edad:**\n**3. 💼 ¿Has trabajado en alianzas antes?**\n"
            "**4. 📊 Alianzas semanales estimadas:**\n**5. 🗣️ ¿Por qué quieres unirte?**\n\n"
            "🔒 *Revisado exclusivamente por el Staff.*"
        )
        await interaction.response.send_message(form_alianzas, ephemeral=True)

class VistaApelacionBotones(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Apelar Sanción", style=discord.ButtonStyle.danger, custom_id="btn_apelar")
    async def boton_apelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ApelacionModal())


# COMANDOS CON PREFIJO a¡

@bot.command(name="postulacion")
async def postulacion(ctx):
    await ctx.send("🛡️ **POSTULACIÓN STAFF — HAKKUZE**\nCopia y responde este formato en privado con un administrador.")

@bot.command(name="caza_alianzas")
async def caza_alianzas(ctx):
    await ctx.send("🤝 **POSTULACIÓN | CAZA ALIANZAS — HAKKUZE**\nCopia y responde este formato...")

@bot.command(name="config")
@commands.has_permissions(administrator=True)
async def config_panel(ctx):
    embed = discord.Embed(
        title="📋 Centro de Postulaciones - Hakkuze",
        description="Selecciona el botón correspondiente al formulario en el que deseas postularte:",
        color=discord.Color.purple()
    )
    embed.set_footer(text="Hakkuze Official • Sistema de Reclutamiento")
    await ctx.send(embed=embed, view=VistaPostulaciones())
    await ctx.message.delete()

@bot.command(name="panel_apelaciones")
@commands.has_permissions(administrator=True)
async def panel_apelaciones(ctx):
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

    await ctx.send(embed=embed, view=VistaApelacionBotones())
    await ctx.message.delete()

@bot.command(name="configurar_apelaciones")
@commands.has_permissions(administrator=True)
async def configurar_apelaciones(ctx, tipo: str, *, valor: str):
    tipo = tipo.lower()
    if tipo == "titulo":
        config_apelacion_embed["titulo"] = valor
    elif tipo == "descripcion":
        config_apelacion_embed["descripcion"] = valor
    elif tipo == "color":
        try: config_apelacion_embed["color"] = int(valor.replace("#", ""), 16)
        except: pass
    elif tipo == "autor":
        config_apelacion_embed["autor"] = None if valor.lower() == "none" else valor
    elif tipo == "thumbnail":
        config_apelacion_embed["thumbnail"] = None if valor.lower() == "none" else valor
    elif tipo == "imagen":
        config_apelacion_embed["image"] = None if valor.lower() == "none" else valor
    elif tipo == "footer":
        config_apelacion_embed["footer"] = None if valor.lower() == "none" else valor
    elif tipo == "ticket_titulo":
        config_apelacion_embed["ticket_titulo"] = valor
    elif tipo == "ticket_descripcion":
        config_apelacion_embed["ticket_descripcion"] = valor
    else:
        await ctx.send("❌ Propiedad no válida. Usa: `titulo`, `descripcion`, `color`, `autor`, `thumbnail`, `imagen`, `footer`, `ticket_titulo`, `ticket_descripcion`")
        return

    await ctx.send(f"✅ ¡Configuración de `{tipo}` actualizada con éxito!")

@bot.command(name="apelaciones_pendientes")
async def apelaciones_pendientes(ctx):
    tiene_rol = any(role.id == ROL_ALTO_MANDO for role in ctx.author.roles)
    if not tiene_rol and not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ No tienes permisos para usar este comando (requiere el rol de Alto Mando).")
        return

    if not apelaciones_db:
        await ctx.send("📂 No hay apelaciones pendientes registradas.")
        return

    embed = discord.Embed(title="📋 Apelaciones Pendientes", color=discord.Color.yellow())
    for i, ap in enumerate(apelaciones_db[:10], 1):
        embed.add_field(
            name=f"#{i} - Usuario: {ap['usuario']}",
            value=f"**ID:** `{ap['id_usuario']}`\n**Razón:** {ap['razon'][:200]}...",
            inline=False
        )

    await ctx.send(embed=embed)

bot.run(os.environ['DISCORD_TOKEN'])
