
import discord

from .metar import metar_get


class DiscordCopilote(discord.Client):

    def __init__(self, **options):
        intents = discord.Intents.default()
        intents.message_content = True  # Nécessaire pour lire le contenu des messages
        self.airport_db = None
        super().__init__(intents=intents, **options)

    def set_airport_db(self, airport_db):
        self.airport_db = airport_db

    async def on_ready(self):
        print(f'Connecté en tant que {self.user}')

    async def run_cmd(self, channel: discord.channel.TextChannel | discord.channel.VoiceChannel, command: str, args: list):
        if command == "INFO" and self.airport_db:
            await self.cmd_info(channel, args)
        elif command == "METAR":
            await self.cmd_metar(channel, args)
        elif command == "HELP":
            await self.cmd_help(channel, args)
        
    
    async def cmd_info(self, channel: discord.channel.TextChannel | discord.channel.VoiceChannel, args: list):
        if len(args) < 1:
            if channel:
                await channel.send("Veuillez fournir un code d'aéroport après 'airport'.")
            return
        for arg in args:
            airport_code = arg.upper()
            try:
                airport = self.airport_db.get_airport(airport_code)
                # print(airport)
            except Exception as e:
                if channel:
                    await channel.send(f"Aéroport {airport_code} Non trouvé. Erreur: {str(e)}")
            else:
                if channel:
                    await channel.send(airport.to_markdown())

    async def cmd_metar(self, channel: discord.channel.TextChannel | discord.channel.VoiceChannel, args: list):
        if len(args) < 1:
            if channel:
                await channel.send("Veuillez fournir un code d'aéroport après 'metar'.")
            return
        for arg in args:
            icao_code = arg.upper()
            try:
                metar_data = metar_get(icao_code)
            except Exception as e:
                if channel:
                    await channel.send(f"Pas de donnée METAR pour {icao_code}")
            else:
                if channel:
                    await channel.send(f"```\n{metar_data}\n```")

    async def cmd_help(self, channel: discord.channel.TextChannel | discord.channel.VoiceChannel, args: list):
        help_text = (
            "Commandes disponibles:\n"
            "- `info <ICAO_CODE> [<ICAO_CODE>] ...`: Obtenir des informations sur une liste aéroport (ex: info LFPG).\n"
            "- `help`: Afficher ce message d'aide.\n"
        )
        if channel:
            await channel.send(help_text)

    async def on_message(self, message):
        
        if message.author == self.user:
            return
        
        # print(f'Message de {message.author}: {message.content}')
        # if message.mentions:
        #     print(f'Mentions: {message.mentions}')

        if self.user in message.mentions:
            message_str = message.content.replace(f'<@{self.user.id}>', '').strip()
            message_split = message_str.split()
            if len(message_split) > 0:
                command = message_split[0].upper()
                args = message_split[1:] if len(message_split) > 1 else []
                await self.run_cmd(message.channel, command, args)
