import discord
from discord import app_commands
from discord.ext import tasks
from typing import Optional
import asyncio
import json
import os
import random
import re
import time
import uuid
from datetime import datetime

# ==========================================================
#  ASTRAL — Alianzas, Afiliaciones y Tickets
# ==========================================================

# ---------- AJUSTES RÁPIDOS ----------
EMOJI_OK = "<a:emoji_40:1560034431060807731>"
EMOJI_ERR = "<a:emoji_40:1560034417643360388>"

# Dónde se guardan los datos. En Railway, si montas un Volume en /data,
# pon la variable DATA_FILE=/data/astral_data.json para no perder nada al redeployar.
DATA_FILE = os.environ.get("DATA_FILE", "astral_data.json")

COMANDOS_VERSION = 1          # súbelo (2, 3...) si algún día cambias comandos y quieres que se resincronicen
AUTO_INTERVALO_MIN = 20       # cada cuántos minutos el Auto Alianza busca pareja
AUTO_COOLDOWN_HORAS = 6       # horas mínimas entre una auto alianza y la siguiente de un mismo servidor
SOLICITUD_EXPIRA_DIAS = 7     # días que una solicitud queda pendiente

# ==========================================================
#  CONFIGURACIÓN DEL SISTEMA DE TICKETS (original, sin tocar)
# ==========================================================
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

# ==========================================================
#  ALMACENAMIENTO (archivo JSON)
# ==========================================================
datos = {"guilds": {}, "solicitudes": {}}


def cargar_datos():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            cargado = json.load(f)
        datos["guilds"] = cargado.get("guilds", {})
        datos["solicitudes"] = cargado.get("solicitudes", {})
        print(f"Datos cargados desde {DATA_FILE}")
    except FileNotFoundError:
        print("No había datos guardados, empezando desde cero.")
    except Exception as e:
        print(f"Error cargando datos: {e}")


def guardar_datos():
    try:
        carpeta = os.path.dirname(DATA_FILE)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_FILE)
    except Exception as e:
        print(f"Error guardando datos: {e}")


def embed_por_defecto(tipo: str) -> dict:
    if tipo == "alianza":
        titulo = "🤝 ¡Nueva Alianza!"
        desc = ("Hemos formado una alianza con **{servidor_aliado}**\n\n"
                "👥 **Miembros:** {miembros_aliado}\n"
                "🔗 **Enlace:** {invitacion_aliado}\n\n"
                "👮 **Hecha por:** {staff}")
    else:
        titulo = "🔗 ¡Nueva Afiliación!"
        desc = ("Nos hemos afiliado con **{servidor_aliado}**\n\n"
                "👥 **Miembros:** {miembros_aliado}\n"
                "🔗 **Enlace:** {invitacion_aliado}\n\n"
                "👮 **Hecha por:** {staff}")
    return {
        "titulo": titulo,
        "descripcion": desc,
        "color": 0x5865F2,
        "imagen": None,
        "thumbnail": "{icono_aliado}",
        "footer": "{servidor} • {fecha}",
        "mensaje": ""
    }


def gdata(gid) -> dict:
    """Datos de un servidor (los crea si no existen)."""
    k = str(gid)
    if k not in datos["guilds"]:
        datos["guilds"][k] = {}
    d = datos["guilds"][k]
    d.setdefault("plantilla", None)
    d.setdefault("cmd_ver", 0)
    d.setdefault("canal_alianzas", None)
    d.setdefault("canal_afiliaciones", None)
    d.setdefault("canal_solicitudes", None)
    d.setdefault("min_miembros", 0)
    d.setdefault("auto", {"activo": False, "canal": None, "ping": "", "minimo": 0, "ultimo": 0})
    d.setdefault("blacklist", {})
    d.setdefault("stats", {})
    d.setdefault("historial", [])
    d.setdefault("embeds", {})
    for t in ("alianza", "afiliacion"):
        if t not in d["embeds"]:
            d["embeds"][t] = embed_por_defecto(t)
    return d


# ==========================================================
#  BOT
# ==========================================================
class Bot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Mantiene vivo el botón del panel de tickets aunque el bot se reinicie
        self.add_view(VistaApelacionBotonesPublico())
        # Comando global: SOLO /plantilla
        await self.tree.sync()
        print("¡Slash commands sincronizados!")


client = Bot()


def registrar_comandos(guild: discord.abc.Snowflake):
    """Registra en ese servidor todos los comandos que se desbloquean con /plantilla."""
    for cmd in COMANDOS_SERVIDOR:
        client.tree.add_command(cmd, guild=discord.Object(id=guild.id), override=True)


@client.event
async def on_ready():
    print(f'¡Bot conectado con éxito como {client.user}!')
    if getattr(client, "_astral_listo", False):
        return
    client._astral_listo = True
    for guild in client.guilds:
        d = gdata(guild.id)
        if d.get("plantilla"):
            registrar_comandos(guild)
            if d.get("cmd_ver") != COMANDOS_VERSION:
                try:
                    await client.tree.sync(guild=discord.Object(id=guild.id))
                    d["cmd_ver"] = COMANDOS_VERSION
                except Exception as e:
                    print(f"No se pudo sincronizar {guild.name}: {e}")
    guardar_datos()
    if not auto_alianza_loop.is_running():
        auto_alianza_loop.start()


@client.event
async def on_guild_join(guild: discord.Guild):
    d = gdata(guild.id)
    if d.get("plantilla"):
        registrar_comandos(guild)
        try:
            await client.tree.sync(guild=discord.Object(id=guild.id))
        except Exception as e:
            print(f"Error sincronizando al entrar a {guild.name}: {e}")


@client.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    print(f"Error en comando: {error!r}")
    msg = f"{EMOJI_ERR} Ocurrió un error inesperado. Intenta de nuevo en unos segundos."
    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass


def verificar_permisos(interaction: discord.Interaction) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    if config_global["admin_rol_id"]:
        rol = interaction.guild.get_role(config_global["admin_rol_id"])
        if rol and rol in interaction.user.roles:
            return True
    return False


# ==========================================================
#  UTILIDADES NUEVAS
# ==========================================================
def es_admin(interaction: discord.Interaction) -> bool:
    return interaction.guild is not None and interaction.user.guild_permissions.administrator


async def solo_admin(interaction: discord.Interaction) -> bool:
    if es_admin(interaction):
        return True
    await interaction.response.send_message(
        f"{EMOJI_ERR} Solo el dueño o alguien con un rol con permiso de **Administración** puede usar esto.",
        ephemeral=True)
    return False


async def permitido(interaction: discord.Interaction) -> bool:
    """Admin + plantilla guardada."""
    if not await solo_admin(interaction):
        return False
    if not gdata(interaction.guild_id).get("plantilla"):
        await interaction.response.send_message(
            f"{EMOJI_ERR} Primero debes guardar la plantilla de tu servidor con `/plantilla`.", ephemeral=True)
        return False
    return True


def canal_valido(guild: discord.Guild, canal_id) -> Optional[discord.TextChannel]:
    """Devuelve el canal solo si existe y el bot puede escribir embeds ahí."""
    if not canal_id:
        return None
    c = guild.get_channel(int(canal_id))
    if isinstance(c, discord.TextChannel):
        p = c.permissions_for(guild.me)
        if p.view_channel and p.send_messages and p.embed_links:
            return c
    return None


def aplicar(texto, vars: dict) -> str:
    if not texto:
        return ""
    for k, v in vars.items():
        texto = texto.replace("{" + k + "}", str(v))
    return texto


def construir_embed(cfg: dict, vars: dict) -> discord.Embed:
    e = discord.Embed(
        title=aplicar(cfg.get("titulo"), vars)[:256] or None,
        description=aplicar(cfg.get("descripcion"), vars)[:4096] or None,
        color=cfg.get("color", 0x5865F2)
    )
    img = aplicar(cfg.get("imagen"), vars).strip()
    if img.startswith("http"):
        e.set_image(url=img)
    th = aplicar(cfg.get("thumbnail"), vars).strip()
    if th.startswith("http"):
        e.set_thumbnail(url=th)
    ft = aplicar(cfg.get("footer"), vars)
    if ft:
        e.set_footer(text=ft[:2048])
    if not e.title and not e.description:
        e.description = "\u200b"
    return e


def construir_vars(g_local: discord.Guild, g_aliado: discord.Guild, staff: str, tipo: str) -> dict:
    dl = gdata(g_local.id)
    da = gdata(g_aliado.id)
    return {
        "servidor": g_local.name,
        "miembros": g_local.member_count or 0,
        "invitacion": dl.get("plantilla") or "",
        "icono": g_local.icon.url if g_local.icon else "",
        "servidor_aliado": g_aliado.name,
        "miembros_aliado": g_aliado.member_count or 0,
        "invitacion_aliado": da.get("plantilla") or "",
        "icono_aliado": g_aliado.icon.url if g_aliado.icon else "",
        "dueno_aliado": f"<@{g_aliado.owner_id}>",
        "staff": staff,
        "fecha": datetime.now().strftime("%d/%m/%Y"),
        "alianzas": sum(1 for h in dl["historial"] if h["tipo"] == "alianza"),
        "afiliaciones": sum(1 for h in dl["historial"] if h["tipo"] == "afiliacion"),
        "tipo": "Alianza" if tipo == "alianza" else "Afiliación",
    }


def vars_ejemplo(guild: discord.Guild, user: discord.abc.User) -> dict:
    dl = gdata(guild.id)
    return {
        "servidor": guild.name,
        "miembros": guild.member_count or 0,
        "invitacion": dl.get("plantilla") or "https://discord.gg/ejemplo",
        "icono": guild.icon.url if guild.icon else "",
        "servidor_aliado": "Servidor de Ejemplo",
        "miembros_aliado": 1234,
        "invitacion_aliado": "https://discord.gg/ejemplo",
        "icono_aliado": guild.icon.url if guild.icon else "",
        "dueno_aliado": user.mention,
        "staff": user.mention,
        "fecha": datetime.now().strftime("%d/%m/%Y"),
        "alianzas": sum(1 for h in dl["historial"] if h["tipo"] == "alianza"),
        "afiliaciones": sum(1 for h in dl["historial"] if h["tipo"] == "afiliacion"),
        "tipo": "Alianza",
    }


VARIABLES_DOC = [
    ("{servidor}", "Nombre de tu servidor"),
    ("{miembros}", "Cantidad de miembros de tu servidor"),
    ("{invitacion}", "Enlace que guardaste con /plantilla"),
    ("{icono}", "URL del icono de tu servidor (para Thumbnail o Imagen)"),
    ("{servidor_aliado}", "Nombre del servidor aliado/afiliado"),
    ("{miembros_aliado}", "Miembros del servidor aliado"),
    ("{invitacion_aliado}", "Enlace del servidor aliado"),
    ("{icono_aliado}", "URL del icono del aliado (para Thumbnail o Imagen)"),
    ("{dueno_aliado}", "Mención del dueño del servidor aliado"),
    ("{staff}", "Staff que hizo la alianza (o 🤖 Auto Alianza)"),
    ("{fecha}", "Fecha de hoy (dd/mm/aaaa)"),
    ("{alianzas}", "Total de alianzas hechas por tu servidor"),
    ("{afiliaciones}", "Total de afiliaciones hechas por tu servidor"),
    ("{tipo}", "Alianza o Afiliación"),
]


def ya_existe(tipo: str, a: int, b: int) -> bool:
    return any(h["tipo"] == tipo and h["aliado_id"] == b for h in gdata(a)["historial"])


def solicitud_pendiente(s: dict) -> bool:
    return s["estado"] == "pendiente" and (time.time() - s["ts"]) < SOLICITUD_EXPIRA_DIAS * 86400


def sumar_stat(d: dict, uid, tipo: str, n: int):
    s = d["stats"].setdefault(str(uid), {"alianzas": 0, "afiliaciones": 0})
    key = "alianzas" if tipo == "alianza" else "afiliaciones"
    s[key] = max(0, s.get(key, 0) + n)


def registrar_union(tipo: str, g_a: discord.Guild, g_b: discord.Guild, uid_a=None, uid_b=None, auto=False):
    ts = datetime.now().isoformat()
    for g, otro, uid in ((g_a, g_b, uid_a), (g_b, g_a, uid_b)):
        d = gdata(g.id)
        d["historial"].append({"tipo": tipo, "aliado_id": otro.id, "aliado_nombre": otro.name,
                               "fecha": ts, "auto": auto})
        if uid:
            sumar_stat(d, uid, tipo, 1)
    guardar_datos()


async def publicar_embed(tipo: str, g_local: discord.Guild, g_aliado: discord.Guild, staff: str,
                         canal: Optional[discord.TextChannel] = None, ping: str = "") -> bool:
    d = gdata(g_local.id)
    if canal is None:
        canal = canal_valido(g_local, d["canal_alianzas"] if tipo == "alianza" else d["canal_afiliaciones"])
    if canal is None:
        return False
    cfg = d["embeds"][tipo]
    vars = construir_vars(g_local, g_aliado, staff, tipo)
    contenido = "\n".join(p for p in (ping, aplicar(cfg.get("mensaje"), vars)) if p).strip()[:2000] or None
    try:
        await canal.send(
            content=contenido,
            embed=construir_embed(cfg, vars),
            allowed_mentions=discord.AllowedMentions(everyone=True, roles=True, users=True))
        return True
    except discord.HTTPException as e:
        print(f"No se pudo publicar en {g_local.name}: {e}")
        return False


# ==========================================================
#  /plantilla  (ÚNICO comando al inicio)
# ==========================================================
RE_PLANTILLA = re.compile(r"(?:discord\.new/|discord(?:app)?\.com/template/)([\w-]+)", re.I)


@client.tree.command(name="plantilla", description="Guarda la plantilla de tu servidor y desbloquea los comandos del bot")
@app_commands.describe(enlace="Enlace de plantilla o de invitación de tu servidor")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def plantilla(interaction: discord.Interaction, enlace: str):
    if not await solo_admin(interaction):
        return
    await interaction.response.defer(ephemeral=True)
    enlace = enlace.strip()
    valido = False
    aviso = ""
    try:
        if RE_PLANTILLA.search(enlace):
            await client.fetch_template(enlace)
            valido = True
        else:
            inv = await client.fetch_invite(enlace)
            valido = inv.guild is not None and inv.guild.id == interaction.guild_id
            if valido and inv.expires_at is not None:
                aviso = "\n⚠️ Este enlace expira. Te recomiendo usar uno **permanente** para que tus aliados siempre puedan entrar."
    except Exception:
        valido = False

    if not valido:
        await interaction.followup.send(
            f"{EMOJI_ERR} Su plantilla no ha sido guardada, por favor coloque un enlace de invitación valido",
            ephemeral=True)
        return

    d = gdata(interaction.guild_id)
    d["plantilla"] = enlace
    guardar_datos()
    registrar_comandos(interaction.guild)
    try:
        await client.tree.sync(guild=discord.Object(id=interaction.guild_id))
        d["cmd_ver"] = COMANDOS_VERSION
        guardar_datos()
    except Exception as e:
        print(f"Error sincronizando comandos: {e}")
    await interaction.followup.send(
        f"{EMOJI_OK} Su plantilla ha sido guardada con éxito{aviso}\n"
        f"Ya puedes usar `/embed alianza`, `/embed afiliacion`, `/leaderboard`, `/variables`, "
        f"`/alianzas_config`, `/solicitar`, `/autoalianza` y `/blacklist`.\n"
        f"*(Si no los ves aún, reinicia Discord con Ctrl+R)*",
        ephemeral=True)


# ==========================================================
#  MODALES PARA EL EDITOR DE TICKETS (original)
# ==========================================================
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
        await interaction.response.send_message(f"✅ ¡{self.campo.capitalize()} actualizado!", ephemeral=True)

# --- VISTA DEL EDITOR VISUAL (tickets) ---

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
                    config_global["color"] = int(self.hex_val.value.replace("#", ""), 16)
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


# ==========================================================
#  COMANDOS DE TICKETS (originales, ahora se desbloquean con /plantilla)
# ==========================================================
@app_commands.command(name="configurar", description="Abre el editor visual avanzado del bot")
@app_commands.guild_only()
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

@app_commands.command(name="configurar_sistema", description="Define los roles y categoría")
@app_commands.guild_only()
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


# ==========================================================
#  INFORMACIÓN Y UTILIDADES (originales)
# ==========================================================
@app_commands.command(name="usuario", description="Muestra información interactiva de un usuario")
@app_commands.describe(miembro="Selecciona al usuario del que quieres ver información")
@app_commands.guild_only()
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

@app_commands.command(name="servidor", description="Muestra información general del servidor")
@app_commands.guild_only()
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

@app_commands.command(name="encuesta", description="Crea una encuesta interactiva rápida")
@app_commands.describe(pregunta="Escribe la pregunta o propuesta para la encuesta")
@app_commands.guild_only()
async def encuesta(interaction: discord.Interaction, pregunta: str):
    embed = discord.Embed(title="📊 Encuesta Oficial", description=pregunta, color=discord.Color.blue())
    embed.set_footer(text=f"Encuesta creada por {interaction.user.name}", icon_url=interaction.user.display_avatar.url)

    await interaction.response.send_message("✅ ¡Encuesta creada con éxito!")
    mensaje = await interaction.original_response()
    await mensaje.add_reaction("👍")
    await mensaje.add_reaction("👎")

@app_commands.command(name="dado", description="Lanza un dado interactivo")
@app_commands.describe(caras="Número de caras del dado (por defecto 6)")
@app_commands.guild_only()
async def dado(interaction: discord.Interaction, caras: int = 6):
    if caras < 2:
        await interaction.response.send_message("❌ El dado debe tener al menos 2 caras.", ephemeral=True)
        return
    resultado = random.randint(1, caras)
    await interaction.response.send_message(f"🎲 {interaction.user.mention} lanzó un dado de {caras} caras y salió: **{resultado}**")


# ==========================================================
#  /embed alianza  y  /embed afiliacion  (editor visual)
# ==========================================================
class ModalCampo(discord.ui.Modal):
    def __init__(self, tipo: str, campo: str, etiqueta: str, largo: bool, max_len: int, actual: str):
        super().__init__(title=f"Editar {etiqueta}"[:45])
        self.tipo = tipo
        self.campo = campo
        self.etiqueta = etiqueta
        self.valor = discord.ui.TextInput(
            label=etiqueta[:45],
            style=discord.TextStyle.paragraph if largo else discord.TextStyle.short,
            default=(actual or "")[:max_len] or None,
            placeholder="Escribe 'none' para dejarlo vacío" if campo in ("imagen", "thumbnail", "footer", "mensaje") else "Escribe aquí...",
            required=True,
            max_length=max_len
        )
        self.add_item(self.valor)

    async def on_submit(self, interaction: discord.Interaction):
        cfg = gdata(interaction.guild_id)["embeds"][self.tipo]
        val = self.valor.value.strip()
        if self.campo == "color":
            try:
                c = int(val.replace("#", ""), 16)
                if not 0 <= c <= 0xFFFFFF:
                    raise ValueError
                cfg["color"] = c
            except ValueError:
                await interaction.response.send_message(f"{EMOJI_ERR} Código HEX inválido. Ejemplo: `#5865F2`", ephemeral=True)
                return
        elif self.campo in ("imagen", "thumbnail", "footer", "mensaje") and val.lower() == "none":
            cfg[self.campo] = None
        else:
            cfg[self.campo] = val
        guardar_datos()
        await interaction.response.send_message(
            f"{EMOJI_OK} **{self.etiqueta}** actualizado. Usa **👁️ Vista previa** para ver cómo queda.", ephemeral=True)


class VistaEditorEmbed(discord.ui.View):
    def __init__(self, tipo: str):
        super().__init__(timeout=900)
        self.tipo = tipo

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await solo_admin(interaction)

    async def _abrir(self, interaction, campo, etiqueta, largo=False, max_len=256):
        cfg = gdata(interaction.guild_id)["embeds"][self.tipo]
        actual = f"#{cfg['color']:06x}" if campo == "color" else (cfg.get(campo) or "")
        await interaction.response.send_modal(ModalCampo(self.tipo, campo, etiqueta, largo, max_len, actual))

    @discord.ui.button(label="✏ Título", style=discord.ButtonStyle.primary, row=0)
    async def b_titulo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._abrir(interaction, "titulo", "Título", False, 256)

    @discord.ui.button(label="📄 Descripción", style=discord.ButtonStyle.primary, row=0)
    async def b_desc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._abrir(interaction, "descripcion", "Descripción", True, 4000)

    @discord.ui.button(label="🎨 Color", style=discord.ButtonStyle.primary, row=0)
    async def b_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._abrir(interaction, "color", "Color (Hex)", False, 7)

    @discord.ui.button(label="🔻 Footer", style=discord.ButtonStyle.primary, row=0)
    async def b_footer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._abrir(interaction, "footer", "Footer", False, 300)

    @discord.ui.button(label="🖼️ Thumbnail", style=discord.ButtonStyle.secondary, row=1)
    async def b_thumb(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._abrir(interaction, "thumbnail", "Thumbnail (URL)", False, 500)

    @discord.ui.button(label="📸 Imagen", style=discord.ButtonStyle.secondary, row=1)
    async def b_imagen(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._abrir(interaction, "imagen", "Imagen (URL)", False, 500)

    @discord.ui.button(label="💬 Mensaje / Ping", style=discord.ButtonStyle.secondary, row=1)
    async def b_mensaje(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._abrir(interaction, "mensaje", "Mensaje fuera del embed", True, 1000)

    @discord.ui.button(label="👁️ Vista previa", style=discord.ButtonStyle.success, row=2)
    async def b_preview(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = gdata(interaction.guild_id)["embeds"][self.tipo]
        vars = vars_ejemplo(interaction.guild, interaction.user)
        contenido = aplicar(cfg.get("mensaje"), vars)[:2000] or None
        await interaction.response.send_message(content=contenido, embed=construir_embed(cfg, vars), ephemeral=True)

    @discord.ui.button(label="♻️ Restablecer", style=discord.ButtonStyle.danger, row=2)
    async def b_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        gdata(interaction.guild_id)["embeds"][self.tipo] = embed_por_defecto(self.tipo)
        guardar_datos()
        await interaction.response.send_message(f"{EMOJI_OK} Embed restablecido a los valores por defecto.", ephemeral=True)


async def abrir_editor(interaction: discord.Interaction, tipo: str):
    if not await permitido(interaction):
        return
    cfg = gdata(interaction.guild_id)["embeds"][tipo]
    vars = vars_ejemplo(interaction.guild, interaction.user)
    nombre = "alianza" if tipo == "alianza" else "afiliación"
    await interaction.response.send_message(
        content=(f"✨ **Editor del embed de {nombre}** (así se verá, con datos de ejemplo)\n"
                 f"Usa los botones para editarlo. Escribe `/variables` para ver todas las variables."),
        embed=construir_embed(cfg, vars),
        view=VistaEditorEmbed(tipo),
        ephemeral=True)


embed_group = app_commands.Group(name="embed", description="Edita los embeds de alianza y afiliación",
                                 guild_only=True, default_permissions=discord.Permissions(administrator=True))


@embed_group.command(name="alianza", description="Edita el embed y mensaje que se publica en las alianzas")
async def embed_alianza(interaction: discord.Interaction):
    await abrir_editor(interaction, "alianza")


@embed_group.command(name="afiliacion", description="Edita el embed y mensaje que se publica en las afiliaciones")
async def embed_afiliacion(interaction: discord.Interaction):
    await abrir_editor(interaction, "afiliacion")


# ==========================================================
#  /variables
# ==========================================================
@app_commands.command(name="variables", description="Muestra todas las variables que puedes usar en los embeds")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def variables(interaction: discord.Interaction):
    if not await permitido(interaction):
        return
    texto = "\n".join(f"`{v}` → {desc}" for v, desc in VARIABLES_DOC)
    embed = discord.Embed(title="🧩 Variables disponibles", description=texto, color=0x5865F2)
    embed.set_footer(text="Úsalas en título, descripción, footer, thumbnail, imagen y mensaje de /embed alianza o /embed afiliacion")
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================================
#  /alianzas_config  (canales y mínimo de miembros)
# ==========================================================
@app_commands.command(name="alianzas_config", description="Configura canales y mínimo de miembros para alianzas y afiliaciones")
@app_commands.describe(
    canal_alianzas="Canal donde se publicarán las alianzas",
    canal_afiliaciones="Canal donde se publicarán las afiliaciones",
    canal_solicitudes="Canal donde llegan las solicitudes de otros servidores",
    minimo_miembros="Mínimo de miembros que debe tener un servidor para aliarse contigo (0 = sin mínimo)")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def alianzas_config(interaction: discord.Interaction,
                          canal_alianzas: Optional[discord.TextChannel] = None,
                          canal_afiliaciones: Optional[discord.TextChannel] = None,
                          canal_solicitudes: Optional[discord.TextChannel] = None,
                          minimo_miembros: Optional[app_commands.Range[int, 0, 10000000]] = None):
    if not await permitido(interaction):
        return
    d = gdata(interaction.guild_id)
    avisos = []
    for clave, canal in (("canal_alianzas", canal_alianzas), ("canal_afiliaciones", canal_afiliaciones),
                         ("canal_solicitudes", canal_solicitudes)):
        if canal:
            d[clave] = canal.id
            if canal_valido(interaction.guild, canal.id) is None:
                avisos.append(f"⚠️ No tengo permisos para enviar embeds en {canal.mention}.")
    if minimo_miembros is not None:
        d["min_miembros"] = minimo_miembros
    guardar_datos()

    def c(cid):
        return f"<#{cid}>" if cid else "*Sin configurar*"

    minimo = d["min_miembros"]
    texto = (f"{EMOJI_OK} **Configuración actual**\n"
             f"• Canal de alianzas: {c(d['canal_alianzas'])}\n"
             f"• Canal de afiliaciones: {c(d['canal_afiliaciones'])}\n"
             f"• Canal de solicitudes: {c(d['canal_solicitudes'])}\n"
             f"• Mínimo de miembros: **{minimo if minimo else 'Sin mínimo'}**")
    if avisos:
        texto += "\n" + "\n".join(avisos)
    await interaction.response.send_message(texto, ephemeral=True)


# ==========================================================
#  /sumar  (alianzas hechas / afiliaciones hechas)
# ==========================================================
@app_commands.command(name="sumar", description="Suma alianzas o afiliaciones hechas a un miembro (usa negativo para restar)")
@app_commands.describe(tipo="Qué quieres sumar", miembro="Miembro del staff", cantidad="Cantidad (por defecto 1)")
@app_commands.choices(tipo=[
    app_commands.Choice(name="Alianzas hechas", value="alianza"),
    app_commands.Choice(name="Afiliaciones hechas", value="afiliacion"),
])
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def sumar(interaction: discord.Interaction, tipo: app_commands.Choice[str], miembro: discord.Member,
                cantidad: app_commands.Range[int, -1000, 1000] = 1):
    if not await permitido(interaction):
        return
    d = gdata(interaction.guild_id)
    sumar_stat(d, miembro.id, tipo.value, cantidad)
    guardar_datos()
    s = d["stats"][str(miembro.id)]
    await interaction.response.send_message(
        f"{EMOJI_OK} {miembro.mention} ahora tiene **{s['alianzas']}** alianzas hechas y **{s['afiliaciones']}** afiliaciones hechas.",
        allowed_mentions=discord.AllowedMentions.none())


# ==========================================================
#  /leaderboard
# ==========================================================
@app_commands.command(name="leaderboard", description="Ranking del staff por alianzas y afiliaciones hechas")
@app_commands.guild_only()
async def leaderboard(interaction: discord.Interaction):
    if not gdata(interaction.guild_id).get("plantilla"):
        await interaction.response.send_message(f"{EMOJI_ERR} Primero debes guardar la plantilla con `/plantilla`.", ephemeral=True)
        return
    stats = gdata(interaction.guild_id)["stats"]
    medallas = ["🥇", "🥈", "🥉"]

    def top(clave):
        lista = sorted(((u, s.get(clave, 0)) for u, s in stats.items() if s.get(clave, 0) > 0),
                       key=lambda x: x[1], reverse=True)[:10]
        if not lista:
            return "Aún no hay datos."
        return "\n".join(f"{medallas[i] if i < 3 else f'`{i + 1}.`'} <@{u}> — **{n}**" for i, (u, n) in enumerate(lista))

    total_a = sum(s.get("alianzas", 0) for s in stats.values())
    total_f = sum(s.get("afiliaciones", 0) for s in stats.values())
    embed = discord.Embed(title="🏆 Leaderboard del Staff", color=0xF1C40F)
    embed.add_field(name="🤝 Alianzas hechas", value=top("alianzas"), inline=True)
    embed.add_field(name="🔗 Afiliaciones hechas", value=top("afiliaciones"), inline=True)
    embed.set_footer(text=f"Total: {total_a} alianzas • {total_f} afiliaciones")
    await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions.none())


# ==========================================================
#  BLACK LIST
# ==========================================================
blacklist_group = app_commands.Group(name="blacklist", description="Gestiona la Black List de servidores",
                                     guild_only=True, default_permissions=discord.Permissions(administrator=True))


@blacklist_group.command(name="agregar", description="Agrega un servidor a la Black List")
@app_commands.describe(servidor_id="ID del servidor", motivo="Motivo (opcional)")
async def bl_agregar(interaction: discord.Interaction, servidor_id: str, motivo: str = "Sin motivo"):
    if not await permitido(interaction):
        return
    sid = servidor_id.strip()
    if not sid.isdigit():
        await interaction.response.send_message(f"{EMOJI_ERR} Debes colocar la **ID** numérica del servidor.", ephemeral=True)
        return
    if sid == str(interaction.guild_id):
        await interaction.response.send_message(f"{EMOJI_ERR} No puedes agregar tu propio servidor.", ephemeral=True)
        return
    g = client.get_guild(int(sid))
    nombre = g.name if g else "Desconocido"
    gdata(interaction.guild_id)["blacklist"][sid] = {"nombre": nombre, "motivo": motivo[:200]}
    guardar_datos()
    await interaction.response.send_message(f"{EMOJI_OK} El servidor **{nombre}** (`{sid}`) fue agregado a la Black List.", ephemeral=True)


async def ac_blacklist(interaction: discord.Interaction, current: str):
    bl = gdata(interaction.guild_id)["blacklist"]
    return [app_commands.Choice(name=f"{v['nombre']} ({k})"[:100], value=k)
            for k, v in bl.items() if current.lower() in v["nombre"].lower() or current in k][:25]


@blacklist_group.command(name="quitar", description="Quita un servidor de la Black List")
@app_commands.describe(servidor="Servidor a quitar")
async def bl_quitar(interaction: discord.Interaction, servidor: str):
    if not await permitido(interaction):
        return
    bl = gdata(interaction.guild_id)["blacklist"]
    if servidor not in bl:
        await interaction.response.send_message(f"{EMOJI_ERR} Ese servidor no está en tu Black List.", ephemeral=True)
        return
    nombre = bl.pop(servidor)["nombre"]
    guardar_datos()
    await interaction.response.send_message(f"{EMOJI_OK} El servidor **{nombre}** fue quitado de la Black List.", ephemeral=True)

bl_quitar.autocomplete("servidor")(ac_blacklist)


@blacklist_group.command(name="ver", description="Muestra tu Black List")
async def bl_ver(interaction: discord.Interaction):
    if not await permitido(interaction):
        return
    bl = gdata(interaction.guild_id)["blacklist"]
    if not bl:
        await interaction.response.send_message("📭 Tu Black List está vacía.", ephemeral=True)
        return
    lineas = [f"• **{v['nombre']}** (`{k}`) — {v['motivo']}" for k, v in list(bl.items())[:25]]
    embed = discord.Embed(title="⛔ Black List", description="\n".join(lineas), color=0xE74C3C)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================================
#  /solicitar alianza  y  /solicitar afiliacion
# ==========================================================
solicitar_group = app_commands.Group(name="solicitar", description="Solicita alianzas o afiliaciones a otros servidores",
                                     guild_only=True, default_permissions=discord.Permissions(administrator=True))


async def ac_servidores(interaction: discord.Interaction, current: str):
    opciones = []
    for g in client.guilds:
        if g.id == interaction.guild_id:
            continue
        if current and current.lower() not in g.name.lower():
            continue
        opciones.append(app_commands.Choice(name=f"{g.name} ({g.member_count} miembros)"[:100], value=str(g.id)))
        if len(opciones) >= 25:
            break
    return opciones


def validar_solicitud(tipo: str, g_origen: discord.Guild, g_destino: discord.Guild) -> Optional[str]:
    """None si todo bien; si no, el motivo."""
    do, dd = gdata(g_origen.id), gdata(g_destino.id)
    nombre = "alianza" if tipo == "alianza" else "afiliación"
    if g_origen.id == g_destino.id:
        return "No puedes enviarte una solicitud a tu propio servidor"
    if not dd.get("plantilla"):
        return "Ese servidor aún no ha configurado el bot"
    if str(g_destino.id) in do["blacklist"]:
        return "Black List (tienes a ese servidor en tu Black List)"
    if str(g_origen.id) in dd["blacklist"]:
        return "Black List"
    minimo = dd.get("min_miembros", 0)
    if minimo and (g_origen.member_count or 0) < minimo:
        return f"No cumple el mínimo de miembros ({minimo})"
    if ya_existe(tipo, g_origen.id, g_destino.id):
        return f"Ya tienen una {nombre} con ese servidor"
    if any(solicitud_pendiente(s) and s["tipo"] == tipo and s["origen"] == g_origen.id and s["destino"] == g_destino.id
           for s in datos["solicitudes"].values()):
        return "Ya hay una solicitud pendiente con ese servidor"
    if canal_valido(g_destino, dd.get("canal_solicitudes")) is None:
        return "Ese servidor no tiene un canal de solicitudes disponible"
    return None


async def procesar_solicitud(interaction: discord.Interaction, tipo: str, servidor: str):
    if not await permitido(interaction):
        return
    nombre = "alianza" if tipo == "alianza" else "afiliación"
    if not servidor.isdigit() or client.get_guild(int(servidor)) is None:
        await interaction.response.send_message(
            f"{EMOJI_ERR} Selecciona un servidor de la lista (el bot debe estar en él).", ephemeral=True)
        return
    await interaction.response.defer()
    origen = interaction.guild
    destino = client.get_guild(int(servidor))
    do = gdata(origen.id)

    # Mínimo de miembros que TÚ pides
    minimo_propio = do.get("min_miembros", 0)
    if minimo_propio and (destino.member_count or 0) < minimo_propio:
        await interaction.followup.send(
            f"{EMOJI_ERR} Este servidor no cumple con el mínimo de miembros (mínimo: {minimo_propio}).")
        return

    motivo = validar_solicitud(tipo, origen, destino)
    if motivo:
        await interaction.followup.send(
            f"{EMOJI_ERR} La solicitud de {nombre} con el servidor **{destino.name}** no ha podido ser enviada, Motivo: {motivo}")
        return

    rid = uuid.uuid4().hex[:10]
    datos["solicitudes"][rid] = {"tipo": tipo, "origen": origen.id, "destino": destino.id,
                                 "usuario": interaction.user.id, "estado": "pendiente", "ts": time.time()}
    guardar_datos()

    embed = discord.Embed(
        title=f"📨 Solicitud de {nombre}",
        description=(f"El servidor **{origen.name}** quiere una {nombre} con ustedes.\n\n"
                     f"👥 **Miembros:** {origen.member_count}\n"
                     f"🔗 **Enlace:** {do.get('plantilla')}\n"
                     f"👮 **Solicitada por:** {interaction.user.mention}"),
        color=0x5865F2)
    if origen.icon:
        embed.set_thumbnail(url=origen.icon.url)
    embed.set_footer(text="Solo alguien con permiso de Administración puede responder")

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Aceptar", style=discord.ButtonStyle.success, custom_id=f"sol|{rid}|ok"))
    view.add_item(discord.ui.Button(label="Rechazar", style=discord.ButtonStyle.danger, custom_id=f"sol|{rid}|no"))

    canal = canal_valido(destino, gdata(destino.id).get("canal_solicitudes"))
    try:
        await canal.send(embed=embed, view=view)
    except Exception as e:
        print(f"Error enviando solicitud: {e}")
        datos["solicitudes"].pop(rid, None)
        guardar_datos()
        await interaction.followup.send(
            f"{EMOJI_ERR} La solicitud de {nombre} con el servidor **{destino.name}** no ha podido ser enviada, Motivo: No se pudo escribir en su canal de solicitudes")
        return

    await interaction.followup.send(
        f"{EMOJI_OK} La solicitud de {nombre} con el servidor **{destino.name}** ha sido enviada con éxito")


@solicitar_group.command(name="alianza", description="Envía una solicitud de alianza a otro servidor donde está el bot")
@app_commands.describe(servidor="Elige el servidor (escribe para buscar)")
async def solicitar_alianza(interaction: discord.Interaction, servidor: str):
    await procesar_solicitud(interaction, "alianza", servidor)


@solicitar_group.command(name="afiliacion", description="Envía una solicitud de afiliación a otro servidor donde está el bot")
@app_commands.describe(servidor="Elige el servidor (escribe para buscar)")
async def solicitar_afiliacion(interaction: discord.Interaction, servidor: str):
    await procesar_solicitud(interaction, "afiliacion", servidor)


solicitar_alianza.autocomplete("servidor")(ac_servidores)
solicitar_afiliacion.autocomplete("servidor")(ac_servidores)


async def avisar_origen(sol: dict, texto: str):
    origen = client.get_guild(sol["origen"])
    enviado = False
    if origen:
        canal = canal_valido(origen, gdata(origen.id).get("canal_solicitudes"))
        if canal:
            try:
                await canal.send(f"<@{sol['usuario']}> {texto}")
                enviado = True
            except Exception:
                pass
    if not enviado:
        try:
            u = await client.fetch_user(sol["usuario"])
            await u.send(texto)
        except Exception:
            pass


async def manejar_boton_solicitud(interaction: discord.Interaction, cid: str):
    try:
        _, rid, accion = cid.split("|")
    except ValueError:
        return
    sol = datos["solicitudes"].get(rid)
    if sol is None or interaction.guild_id != sol["destino"]:
        await interaction.response.send_message(f"{EMOJI_ERR} Esta solicitud ya no existe.", ephemeral=True)
        return
    if not es_admin(interaction):
        await interaction.response.send_message(
            f"{EMOJI_ERR} Solo alguien con permiso de **Administración** puede responder.", ephemeral=True)
        return
    if sol["estado"] != "pendiente" or not solicitud_pendiente(sol):
        await interaction.response.send_message(f"{EMOJI_ERR} Esta solicitud ya fue respondida o expiró.", ephemeral=True)
        return

    await interaction.response.defer()
    destino = interaction.guild
    origen = client.get_guild(sol["origen"])
    tipo = sol["tipo"]
    nombre = "alianza" if tipo == "alianza" else "afiliación"
    emb = interaction.message.embeds[0] if interaction.message.embeds else discord.Embed(title="Solicitud")

    if accion == "no":
        sol["estado"] = "rechazada"
        guardar_datos()
        emb.color = 0xE74C3C
        emb.set_footer(text=f"❌ Rechazada por {interaction.user}")
        await interaction.message.edit(embed=emb, view=None)
        await avisar_origen(sol, f"{EMOJI_ERR} **{destino.name}** rechazó tu solicitud de {nombre}.")
        return

    if origen is None:
        sol["estado"] = "expirada"
        guardar_datos()
        await interaction.followup.send(f"{EMOJI_ERR} El bot ya no está en el servidor que envió la solicitud.", ephemeral=True)
        return
    if ya_existe(tipo, origen.id, destino.id):
        sol["estado"] = "aceptada"
        guardar_datos()
        await interaction.followup.send(f"{EMOJI_ERR} Ya tienen una {nombre} con ese servidor.", ephemeral=True)
        return

    sol["estado"] = "aceptada"
    registrar_union(tipo, origen, destino, uid_a=sol["usuario"], uid_b=interaction.user.id)
    ok_destino = await publicar_embed(tipo, destino, origen, interaction.user.mention)
    ok_origen = await publicar_embed(tipo, origen, destino, f"<@{sol['usuario']}>")

    emb.color = 0x2ECC71
    emb.set_footer(text=f"✅ Aceptada por {interaction.user}")
    await interaction.message.edit(embed=emb, view=None)

    msg = f"{EMOJI_OK} ¡{nombre.capitalize()} con **{origen.name}** realizada!"
    if not ok_destino:
        msg += f"\n⚠️ No pude publicarla en tu servidor: configura el canal con `/alianzas_config` y dame permisos de enviar embeds."
    await interaction.followup.send(msg, ephemeral=True)

    aviso = f"{EMOJI_OK} **{destino.name}** aceptó tu solicitud de {nombre}. ¡Ya está hecha!"
    if not ok_origen:
        aviso += "\n⚠️ No pude publicarla en tu servidor: configura el canal con `/alianzas_config`."
    await avisar_origen(sol, aviso)


@client.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type is discord.InteractionType.component:
        cid = (interaction.data or {}).get("custom_id", "")
        if cid.startswith("sol|"):
            await manejar_boton_solicitud(interaction, cid)


# ==========================================================
#  AUTO ALIANZA
# ==========================================================
autoalianza_group = app_commands.Group(name="autoalianza", description="Sistema de Auto Alianza",
                                       guild_only=True, default_permissions=discord.Permissions(administrator=True))

auto_lock = asyncio.Lock()


def auto_activos() -> list:
    res = []
    for g in client.guilds:
        d = gdata(g.id)
        a = d["auto"]
        if a.get("activo") and d.get("plantilla") and canal_valido(g, a.get("canal")):
            res.append(g)
    return res


def auto_compatibles(g: discord.Guild, h: discord.Guild) -> bool:
    dg, dh = gdata(g.id), gdata(h.id)
    if ya_existe("alianza", g.id, h.id) or ya_existe("alianza", h.id, g.id):
        return False
    if str(h.id) in dg["blacklist"] or str(g.id) in dh["blacklist"]:
        return False
    if dg["auto"].get("minimo", 0) > (h.member_count or 0):
        return False
    if dh["auto"].get("minimo", 0) > (g.member_count or 0):
        return False
    return True


async def ejecutar_auto():
    async with auto_lock:
        ahora = time.time()
        cooldown = AUTO_COOLDOWN_HORAS * 3600
        activos = [g for g in auto_activos() if ahora - gdata(g.id)["auto"].get("ultimo", 0) >= cooldown]
        random.shuffle(activos)
        usados = set()
        for g in activos:
            if g.id in usados:
                continue
            candidatos = [h for h in activos if h.id != g.id and h.id not in usados and auto_compatibles(g, h)]
            if not candidatos:
                continue
            h = random.choice(candidatos)
            usados.update({g.id, h.id})
            registrar_union("alianza", g, h, auto=True)
            for x in (g, h):
                gdata(x.id)["auto"]["ultimo"] = ahora
            guardar_datos()
            for local, otro in ((g, h), (h, g)):
                a = gdata(local.id)["auto"]
                await publicar_embed("alianza", local, otro, "🤖 Auto Alianza",
                                     canal=canal_valido(local, a.get("canal")), ping=a.get("ping", ""))
            print(f"Auto alianza: {g.name} <-> {h.name}")


@tasks.loop(minutes=AUTO_INTERVALO_MIN)
async def auto_alianza_loop():
    try:
        await ejecutar_auto()
    except Exception as e:
        print(f"Error en auto alianza: {e}")


@auto_alianza_loop.before_loop
async def antes_auto():
    await client.wait_until_ready()


@autoalianza_group.command(name="activar", description="Activa la Auto Alianza en tu servidor")
@app_commands.describe(
    canal="Canal donde se publicarán las auto alianzas",
    ping="Rol a mencionar en cada auto alianza (elige @everyone para mencionar a todos)",
    minimo_miembros="OPCIONAL: mínimo de miembros que debe tener el otro servidor")
async def auto_activar(interaction: discord.Interaction, canal: discord.TextChannel,
                       ping: Optional[discord.Role] = None,
                       minimo_miembros: Optional[app_commands.Range[int, 0, 10000000]] = 0):
    if not await permitido(interaction):
        return
    if canal_valido(interaction.guild, canal.id) is None:
        await interaction.response.send_message(
            f"{EMOJI_ERR} No tengo permisos para ver, escribir y enviar embeds en {canal.mention}.", ephemeral=True)
        return
    d = gdata(interaction.guild_id)
    if ping is None:
        ping_txt = ""
    elif ping.id == interaction.guild_id:
        ping_txt = "@everyone"
    else:
        ping_txt = ping.mention
    d["auto"].update({"activo": True, "canal": canal.id, "ping": ping_txt, "minimo": minimo_miembros or 0})
    guardar_datos()
    await interaction.response.send_message(
        f"{EMOJI_OK} **Auto Alianza activada**\n"
        f"• Canal: {canal.mention}\n"
        f"• Ping: {ping_txt or 'Ninguno'}\n"
        f"• Mínimo de miembros: {minimo_miembros or 'Sin mínimo'}\n"
        f"El bot buscará servidores que también tengan la Auto Alianza activada y hará la alianza automáticamente.",
        ephemeral=True)
    asyncio.create_task(ejecutar_auto())


@autoalianza_group.command(name="desactivar", description="Desactiva la Auto Alianza en tu servidor")
async def auto_desactivar(interaction: discord.Interaction):
    if not await permitido(interaction):
        return
    gdata(interaction.guild_id)["auto"]["activo"] = False
    guardar_datos()
    await interaction.response.send_message(f"{EMOJI_OK} **Auto Alianza desactivada.**", ephemeral=True)


@autoalianza_group.command(name="estado", description="Muestra la configuración de tu Auto Alianza")
async def auto_estado(interaction: discord.Interaction):
    if not await permitido(interaction):
        return
    a = gdata(interaction.guild_id)["auto"]
    canal_txt = "<#" + str(a["canal"]) + ">" if a.get("canal") else "Sin configurar"
    estado_txt = "✅ Activada" if a.get("activo") else "❌ Desactivada"
    await interaction.response.send_message(
        f"🤖 **Auto Alianza:** {estado_txt}\n"
        f"• Canal: {canal_txt}\n"
        f"• Ping: {a.get('ping') or 'Ninguno'}\n"
        f"• Mínimo de miembros: {a.get('minimo') or 'Sin mínimo'}",
        ephemeral=True)


# ==========================================================
#  LISTA DE COMANDOS QUE SE DESBLOQUEAN CON /plantilla
# ==========================================================
COMANDOS_SERVIDOR = [
    embed_group, leaderboard, variables, alianzas_config, sumar,
    solicitar_group, autoalianza_group, blacklist_group,
    configurar, configurar_sistema, usuario, servidor, encuesta, dado,
]

cargar_datos()
client.run(os.environ['DISCORD_TOKEN'])
