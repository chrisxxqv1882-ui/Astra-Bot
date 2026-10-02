import discord
from discord import app_commands
import os

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

client.run(os.environ['DISCORD_TOKEN'])
