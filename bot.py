import discord
from discord import app_commands
import os
import random

# Configuración global editable
config_global = {
    "admin_rol_id": None, 
    "rol_id": 1549479823200747521,
    "categoria_id": None,
    "titulo": "⚖️ Sistema de Apelaciones y Reclamaciones",
    "descripcion": "Si necesitas abrir un ticket, reclamar o apelar una sanción, haz clic en el botón de abajo.",
    "color": 0x3498db,
    "autor": "Hakkuze - Moderación",
    "thumbnail": None,
    "image": None,
    "footer": "Sistema seguro de tickets",
    "ticket_embed_titulo": "📥 ¡Nuevo Ticket Abierto!",
    "ticket_embed_descripcion": "El usuario {usuario} ha iniciado un caso.\n\n**Motivo / Razón:**\n{razon}",
    "ticket_embed_footer": "Atiende con respeto y profesionalismo."
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

def verificar_permisos(interaction: discord.Interaction) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    if config_global["admin_rol_id"]:
        rol = interaction.guild.get_role(config_global["admin_rol_id"])
        if rol and rol in interaction.user.roles:
            return True
    return False

# --- MODALES PARA EL EDITOR VISUAL ---

class ModalEditarTexto(discord.ui.Modal):
    def __init__(self, campo: str):
        super().__init__(title=f"Editar {campo.replace('_', ' ').capitalize()}")
        self.campo = campo
        
        self.valor = discord.ui.TextInput(
            label="Nuevo valor",
            style=discord.TextStyle.paragraph if "descripcion" in campo else discord.TextStyle.short,
            placeholder="Escribe aquí...",
            required=True,
            max_length=1000
        )
        self.add_item(self.valor)

    async def on_submit(self, interaction: discord.Interaction):
        config_global[self.campo] = self.valor.value
        await interaction.response.send_message(f"✅ ¡{self.campo.replace('_', ' ').capitalize()} actualizado con éxito!", ephemeral=True)

class ModalEditarURLs(discord.ui.Modal):
    def __init__(self, campo: str):
        super().__init__(title=f"Editar {campo.capitalize()}")
        self.campo = campo
        
        self.valor = discord.ui.TextInput(
            label="Enlace URL (o escribe 'none' para quitar)",
            style=discord.TextStyle.short,
            placeholder="https://...",
            required=True
        )
        self.add_item(self.valor)

    async def on_submit(self, interaction: discord.Interaction):
        val = self.valor.value.strip()
        config_global[self.campo] = None if val.lower() == "none" else val
        await interaction.response.send_message(f"✅ ¡{self.capitalize()} actualizado!", ephemeral=True)

# --- VISTA DEL EDITOR VISUAL ---

class VistaEditorVisual(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✏ Título Panel", style=discord.ButtonStyle.primary, row=0)
    async def btn_titulo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarTexto("titulo"))

    @discord.ui.button(label="📄 Desc. Panel", style=discord.ButtonStyle.primary, row=0)
    async def btn_desc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarTexto("descripcion"))

    @discord.ui.button(label="🎨 Color (Hex)", style=discord.ButtonStyle.primary, row=0)
    async def btn_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        class ModalColor(discord.ui.Modal, title="Editar Color"):
            hex_val = discord.ui.TextInput(label="Código Hex (ej: #3498db)", placeholder="#3498db", required=True)
            async def on_submit(self, inter: discord.Interaction):
                try:
                    config_global["color"] = int(hex_val.value.replace("#", ""), 16)
                    await inter.response.send_message("✅ ¡Color actualizado!", ephemeral=True)
                except:
                    await inter.response.send_message("❌ Código HEX inválido.", ephemeral=True)
        await interaction.response.send_modal(ModalColor())

    @discord.ui.button(label="📥 Título Ticket", style=discord.ButtonStyle.secondary, row=1)
    async def btn_tticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarTexto("ticket_embed_titulo"))

    @discord.ui.button(label="📄 Desc. Ticket", style=discord.ButtonStyle.secondary, row=1)
    async def btn_dticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarTexto("ticket_embed_descripcion"))

    @discord.ui.button(label="🖼️ Thumbnail", style=discord.ButtonStyle.success, row=2)
    async def btn_thumb(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarURLs("thumbnail"))

    @discord.ui.button(label="📸 Imagen", style=discord.ButtonStyle.success, row=2)
    async def btn_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalEditarURLs("image"))

    @discord.ui.button(label="🚀 Publicar Panel", style=discord.ButtonStyle.danger, row=2)
    async def btn_publicar(self, interaction: discord.Interaction, button: discord.ui.Button):
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
        await interaction.response.send_message("✅ ¡Panel de tickets publicado con éxito!", ephemeral=True)

class VistaApelacionBotonesPublico(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Abrir Ticket / Reclamación", style=discord.ButtonStyle.danger, custom_id="btn_abrir_ticket")
    async def boton_apelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ApelacionModal())

class ApelacionModal(discord.ui.Modal, title="Formulario de Reclamación / Ticket"):
    razon = discord.ui.TextInput(
        label="Motivo de tu ticket o reclamación",
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
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True)
        }
        if rol_obj: overwrites[rol_obj] = discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True)

        canal = await guild.create_text_channel(f"ticket-{interaction.user.name}".lower(), category=categoria, overwrites=overwrites)
        if canal:
            embed_ticket = discord.Embed(
                title=config_global["ticket_embed_titulo"],
                description=config_global["ticket_embed_descripcion"].format(usuario=interaction.user.mention, razon=self.razon.value),
                color=config_global["color"]
            )
            embed_ticket.set_footer(text=config_global["ticket_embed_footer"])
            
            class VistaCerrarTicket(discord.ui.View):
                @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.secondary, custom_id="cerrar_tk")
                async def cerrar(self, inter: discord.Interaction, btn: discord.ui.Button):
                    await inter.response.send_message("🔒 Cerrando canal en 3 segundos...")
                    import asyncio
                    await asyncio.sleep(3)
                    await inter.channel.delete()

            mencion = f"<@&{config_global['rol_id']}>" if rol_obj else ""
            await canal.send(content=f"{mencion} ¡Nuevo ticket abierto por {interaction.user.mention}!", embed=embed_ticket, view=VistaCerrarTicket())
            await interaction.response.send_message(f"✅ ¡Tu ticket ha sido creado correctamente en {canal.mention}!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Hubo un error al crear el canal.", ephemeral=True)


# --- COMANDOS DE CONFIGURACIÓN ---

@client.tree.command(name="configurar", description="Abre el editor visual avanzado del bot")
async def configurar(interaction: discord.Interaction):
    if not verificar_permisos(interaction):
        await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
        return

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
        content="✨ **Editor Visual del Sistema de Tickets**\nUsa los botones para personalizar el panel público y el mensaje interno:",
        embed=embed_preview,
        view=VistaEditorVisual(),
        ephemeral=True
    )

@client.tree.command(name="configurar_sistema", description="Define los roles y categoría")
async def configurar_sistema(interaction: discord.Interaction, rol_comandos: discord.Role = None, rol_staff: discord.Role = None, categoria_id: str = None):
    if not verificar_permisos(interaction):
        await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
        return

    texto_resp = "✅ **Configuración actualizada:**\n"
    if rol_comandos:
        config_global["admin_rol_id"] = rol_comandos.id
        texto_resp += f"- Rol comandos: {rol_comandos.mention}\n"
    if rol_staff:
        config_global["rol_id"] = rol_staff.id
        texto_resp += f"- Rol staff tickets: {rol_staff.mention}\n"
    if categoria_id:
        config_global["categoria_id"] = categoria_id
        texto_resp += f"- Categoría ID: `{categoria_id}`\n"

    await interaction.response.send_message(texto_resp, ephemeral=True)


# --- COMANDOS DE INFORMACIÓN Y UTILIDADES INTERACTIVAS ---

@client.tree.command(name="usuario", description="Muestra información interactiva de un usuario")
@app_commands.describe(miembro="Selecciona al usuario del que quieres ver información")
async def usuario(interaction: discord.Interaction, miembro: discord.Member = None):
    usuario_obj = miembro if miembro else interaction.user
    embed = discord.Embed(title=f"👤 Información de {usuario_obj.name}", color=usuario_obj.color)
    embed.set_thumbnail(url=usuario_obj.display_avatar.url)
    embed.add_field(name="🆔 ID", value=usuario_obj.id, inline=True)
    embed.add_field(name="📅 Creación de cuenta", value=usuario_obj.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="📥 Ingreso al servidor", value=usuario_obj.joined_at.strftime("%d/%m/%Y") if usuario_obj.joined_at else "Desconocido", inline=True)
    
    roles = [role.mention for role in usuario_obj.roles if role != interaction.guild.default_role]
    roles_str = ", ".join(roles) if roles else "Ninguno"
    if len(roles_str) > 1024: roles_str = "Muchos roles asignados"
    embed.add_field(name=f"🛡️ Roles ({len(roles)})", value=roles_str, inline=False)
    
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="servidor", description="Muestra información general del servidor")
async def servidor(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"📊 Información de {guild.name}", color=discord.Color.purple())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="👑 Owner", value=guild.owner.mention if guild.owner else "Desconocido", inline=True)
    embed.add_field(name="👥 Miembros", value=str(guild.member_count), inline=True)
    embed.add_field(name="📅 Creación", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="💬 Canales de texto", value=str(len(guild.text_channels)), inline=True)
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="encuesta", description="Crea una encuesta interactiva rápida")
@app_commands.describe(pregunta="Escribe la pregunta o propuesta para la encuesta")
async def encuesta(interaction: discord.Interaction, pregunta: str):
    embed = discord.Embed(title="📊 Encuesta Oficial", description=pregunta, color=discord.Color.blue())
    embed.set_footer(text=f"Encuesta creada por {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message("✅ ¡Encuesta creada con éxito!")
    mensaje = await interaction.original_response()
    await mensaje.add_reaction("👍")
    await mensaje.add_reaction("👎")

@client.tree.command(name="dado", description="Lanza un dado interactivo")
@app_commands.describe(caras="Número de caras del dado (por defecto 6)")
async def dado(interaction: discord.Interaction, caras: int = 6):
    if caras < 2:
        await interaction.response.send_message("❌ El dado debe tener al menos 2 caras.", ephemeral=True)
        return
    resultado = random.randint(1, caras)
    await interaction.response.send_message(f"🎲 {interaction.user.mention} lanzó un dado de {caras} caras y salió: **{resultado}**")

client.run(os.environ['DISCORD_TOKEN'])
