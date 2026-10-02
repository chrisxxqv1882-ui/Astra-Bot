import discord
from discord import app_commands
import os

# Configuración inicial global editable
config_global = {
    "rol_id": 1549479823200747521,
    "categoria_id": None,
    "titulo": "⚖️ Sistema de Apelaciones",
    "descripcion": "Si fuiste sancionado y deseas apelar, haz clic en el botón de abajo para rellenar tu formulario.",
    "color": 0x3498db,
    "autor": "Hakkuze - Moderación",
    "thumbnail": None,
    "image": None,
    "footer": "Sistema seguro de apelaciones",
    "ticket_titulo": "📥 ¡Nueva Apelación Recibida!",
    "ticket_descripcion": "El usuario {usuario} ha enviado una apelación.\n\n**Motivo:**\n{razon}"
}

apelaciones_db = []

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

# --- MODALES PARA EDITAR CADA PARTE DEL EMBED VISUALMENTE ---

class ModalEditarTexto(discord.ui.Modal):
    def __init__(self, campo: str):
        super().__init__(title=f"Editar {campo.capitalize()}")
        self.campo = campo
        
        self.valor = discord.ui.TextInput(
            label=f"Nuevo valor para {campo}",
            style=discord.TextStyle.paragraph if campo in ["descripcion", "ticket_descripcion"] else discord.TextStyle.short,
            placeholder="Escribe aquí...",
            required=True,
            max_length=1000
        )
        self.add_item(self.valor)

    async def on_submit(self, interaction: discord.Interaction):
        config_global[self.campo] = self.valor.value
        await interaction.response.send_message(f"✅ ¡{self.campo.capitalize()} actualizado con éxito!", ephemeral=True)

class ModalEditarURLs(discord.ui.Modal):
    def __init__(self, campo: str):
        super().__init__(title=f"Editar {campo.capitalize()}")
        self.campo = campo
        
        self.valor = discord.ui.TextInput(
            label=f"Enlace URL (o escribe 'none' para quitar)",
            style=discord.TextStyle.short,
            placeholder="https://...",
            required=True
        )
        self.add_item(self.valor)

    async def on_submit(self, interaction: discord.Interaction):
        val = self.valor.value.strip()
        config_global[self.campo] = None if val.lower() == "none" else val
        await interaction.response.send_message(f"✅ ¡{self.campo.capitalize()} actualizado!", ephemeral=True)

# --- VISTA CON LOS BOTONES DEL EDITOR VISUAL ---

class VistaEditorVisual(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✏️️ Título", style=discord.ButtonStyle.primary, row=0)
    async def btn_titulo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarTexto("titulo"))

    @discord.ui.button(label="👤 Autor", style=discord.ButtonStyle.primary, row=0)
    async def btn_autor(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarTexto("autor"))

    @discord.ui.button(label="📄 Descripción", style=discord.ButtonStyle.primary, row=0)
    async def btn_desc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarTexto("descripcion"))

    @discord.ui.button(label="🎨 Color (Hex)", style=discord.ButtonStyle.primary, row=0)
    async def btn_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        class ModalColor(discord.ui.Modal, title="Editar Color"):
            hex_val = discord.ui.TextInput(label="Código Hex (ej: #ff0000)", placeholder="#3498db", required=True)
            async def on_submit(self, inter: discord.Interaction):
                try:
                    config_global["color"] = int(hex_val.value.replace("#", ""), 16)
                    await inter.response.send_message("✅ ¡Color actualizado!", ephemeral=True)
                except:
                    await inter.response.send_message("❌ Código HEX inválido.", ephemeral=True)
        await interaction.response.send_modal(ModalColor())

    @discord.ui.button(label="📌 Footer (Pie)", style=discord.ButtonStyle.secondary, row=1)
    async def btn_footer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarTexto("footer"))

    @discord.ui.button(label="🖼️ Thumbnail (Miniatura)", style=discord.ButtonStyle.secondary, row=1)
    async def btn_thumb(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarURLs("thumbnail"))

    @discord.ui.button(label="📸 Imagen Grande", style=discord.ButtonStyle.secondary, row=1)
    async def btn_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarURLs("image"))

    @discord.ui.button(label="🚀 Publicar Panel", style=discord.ButtonStyle.success, row=2)
    async def btn_publicar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Generar el embed final para publicar
        embed = discord.Embed(
            title=config_global["titulo"],
            description=config_global["descripcion"],
            color=config_global["color"]
        )
        if config_global["autor"]: embed.set_author(name=config_global["autor"])
        if config_global["thumbnail"]: embed.set_thumbnail(url=config_global["thumbnail"])
        if config_global["image"]: embed.set_image(url=config_global["image"])
        if config_global["footer"]: embed.set_footer(text=config_global["footer"])

        await interaction.channel.send(embed=embed, view=VistaApelacionBotonesPublico())
        await interaction.response.send_message("✅ ¡Panel de apelaciones publicado oficialmente en este canal!", ephemeral=True)

# Botón público para que los usuarios abran el formulario de apelación
class VistaApelacionBotonesPublico(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Apelar Sanción", style=discord.ButtonStyle.danger, custom_id="btn_apelar_user")
    async def boton_apelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ApelacionModal())

class ApelacionModal(discord.ui.Modal, title="Formulario de Apelación"):
    razon = discord.ui.TextInput(
        label="¿Por qué deberíamos aceptar tu apelación?",
        style=discord.TextStyle.paragraph,
        placeholder="Explica detalladamente tu caso...",
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        apelaciones_db.append({"usuario": str(interaction.user), "id_usuario": interaction.user.id, "razon": self.razon.value})
        guild = interaction.guild
        rol_obj = guild.get_role(config_global["rol_id"])
        categoria = discord.utils.get(guild.categories, id=int(config_global["categoria_id"])) if config_global["categoria_id"] else None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if rol_obj: overwrites[rol_obj] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        canal = await guild.create_text_channel(f"apelacion-{interaction.user.name}".lower(), category=categoria, overwrites=overwrites)
        if canal:
            embed_aviso = discord.Embed(
                title=config_global["ticket_titulo"],
                description=config_global["ticket_descripcion"].format(usuario=interaction.user.mention, razon=self.razon.value),
                color=config_global["color"]
            )
            mencion = f"<@&{config_global['rol_id']}>" if rol_obj else ""
            await canal.send(content=f"{mencion} ¡Nueva apelación creada!", embed=embed_aviso)
            await interaction.response.send_message(f"✅ ¡Creado en {canal.mention}!", ephemeral=True)


# --- COMANDOS PRINCIPALES ---

@client.tree.command(name="configurar", description="Abre el panel visual e interactivo para diseñar el embed de apelaciones")
@app_commands.checks.has_permissions(administrator=True)
async def configurar(interaction: discord.Interaction):
    embed_preview = discord.Embed(
        title=config_global["titulo"],
        description=config_global["descripcion"],
        color=config_global["color"]
    )
    if config_global["autor"]: embed_preview.set_author(name=config_global["autor"])
    if config_global["thumbnail"]: embed_preview.set_thumbnail(url=config_global["thumbnail"])
    if config_global["image"]: embed_preview.set_image(url=config_global["image"])
    if config_global["footer"]: embed_preview.set_footer(text=config_global["footer"])

    await interaction.response.send_message(
        content="✨ **Editor Visual de Apelaciones**\nUsa los botones de abajo para personalizar cada parte del embed en tiempo real:",
        embed=embed_preview,
        view=VistaEditorVisual(),
        ephemeral=True
    )

@client.tree.command(name="configurar_sistema", description="Define el rol del staff y la categoría de los canales de ticket")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(rol="Rol del staff que atenderá", categoria_id="ID de la categoría de Discord")
async def configurar_sistema(interaction: discord.Interaction, rol: discord.Role, categoria_id: str):
    config_global["rol_id"] = rol.id
    config_global["categoria_id"] = categoria_id
    await interaction.response.send_message(f"✅ Sistema configurado: Rol {rol.mention} y Categoría ID `{categoria_id}`.", ephemeral=True)


@client.tree.command(name="apelaciones_pendientes", description="Muestra la lista de apelaciones registradas")
async def apelaciones_pendientes(interaction: discord.Interaction):
    tiene_rol = any(role.id == config_global["rol_id"] for role in interaction.user.roles)
    if not tiene_rol and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
        return
    if not apelaciones_db:
        await interaction.response.send_message("📂 No hay apelaciones pendientes.", ephemeral=True)
        return

    embed = discord.Embed(title="📋 Apelaciones Registradas", color=discord.Color.yellow())
    for i, ap in enumerate(apelaciones_db[:10], 1):
        embed.add_field(name=f"#{i} - {ap['usuario']}", value=f"**ID:** `{ap['id_usuario']}`\n**Razón:** {ap['razon'][:200]}...", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

client.run(os.environ['DISCORD_TOKEN'])