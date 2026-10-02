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

client.run(os.environ['DISCORD_TOKEN'])
