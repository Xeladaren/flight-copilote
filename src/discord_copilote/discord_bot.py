
import discord
import argparse

from .metar import metar_get


class DiscordCopilote(discord.Client):

    def __init__(self, **options):
        intents = discord.Intents.default()
        intents.message_content = True  # Nécessaire pour lire le contenu des messages
        self.airport_db = None
        self.meteo_france = None
        super().__init__(intents=intents, **options)

    def set_airport_db(self, airport_db):
        self.airport_db = airport_db

    def set_meteo_france(self, meteo_france):
        self.meteo_france = meteo_france

    async def on_ready(self):
        print(f'Connecté en tant que {self.user}')
        
    async def cmd_info(self, args):
        # print(f"cmd_info called with args: {args}")

        if len(args.icao_codes) < 1:
            if args.channel:
                await args.channel.send("Veuillez fournir au moins un code ICAO d'aéroport.")
            return
        for icao_code in args.icao_codes:
            icao_code = icao_code.upper()
            try:
                airport = self.airport_db.get_airport(icao_code)
                # print(airport)
            except Exception as e:
                if args.channel:
                    await args.channel.send(f"Aéroport {icao_code} Non trouvé. Erreur: {str(e)}")
            else:
                if args.channel:
                    await args.channel.send(airport.to_markdown(meteo_france=self.meteo_france))

    async def cmd_metar(self, args):
        # print(f"cmd_metar called with args: {args}")

        if len(args.icao_codes) < 1:
            if args.channel:
                await args.channel.send("Veuillez fournir au moins un code ICAO d'aéroport.")
            return
        for icao_code in args.icao_codes:
            icao_code = icao_code.upper()
            try:
                metar_data = metar_get(icao_code)
            except Exception as e:
                if self.meteo_france:
                    try:
                        airport = self.airport_db.get_airport(icao_code)
                        station, distance = self.meteo_france.get_closest_station(airport.position()[0], airport.position()[1])
                        observation = self.meteo_france.get_observation_6m(station)
                        if distance < 2:
                            md = f"*Données Meteo France de la station à proximité de {airport.icao_code()}*\n"
                            metar_data = observation.to_metar(airport_oaci_code=airport.icao_code())
                        else:
                            md = f"*Données Meteo France de la station {station.name} à {distance/1.852:.1f} nm de {airport.icao_code()}*\n"
                            metar_data = observation.to_metar(airport_oaci_code=airport.icao_code())
                        md += f"```\n{metar_data}\n```\n"
                        await args.channel.send(md)
                    except Exception as e:
                        print(str(e))
                        await args.channel.send(f"Pas de donnée METAR pour {icao_code}")
                elif args.channel:
                    await args.channel.send(f"Pas de donnée METAR pour {icao_code}")
            else:
                if args.channel:
                    await args.channel.send(f"```\n{metar_data}\n```")

    async def on_message(self, message):
        
        if message.author == self.user:
            return
        
        # print(f'Message de {message.author}: {message.content}')
        # if message.mentions:
        #     print(f'Mentions: {message.mentions}')

        if self.user in message.mentions:
            message_str = message.content.replace(f'<@{self.user.id}>', '').strip()

            parser = argparse.ArgumentParser(prog=f"<@{self.user.id}>", add_help=False)
            parser.add_argument("--help", "-h", action="store_true", help="Show this help message and exit")

            subparsers = parser.add_subparsers(dest='command')
            parser_info  = subparsers.add_parser('info',  add_help=False, help='Get airport information')
            parser_info.add_argument('icao_codes', nargs='*', help='List of ICAO airport codes')
            parser_info.add_argument('--help', '-h', action='store_true', help='Show this help message and exit')
            parser_info.set_defaults(channel=message.channel, func=self.cmd_info, parser=parser_info)

            parser_metar = subparsers.add_parser('metar', add_help=False, help='Get METAR information')
            parser_metar.add_argument('icao_codes', nargs='*', help='List of ICAO airport codes')
            parser_metar.add_argument('--help', '-h', action='store_true', help='Show this help message and exit')
            parser_metar.set_defaults(channel=message.channel, func=self.cmd_metar, parser=parser_metar)

            args = parser.parse_args(message_str.split())

            if args.help and args.command and hasattr(args, 'parser'):

                help_text = args.parser.format_help()
                if message.channel:
                    await message.channel.send(help_text)
                else:
                    print(help_text)

            elif args.command is None:
                help_text = parser.format_help()
                if message.channel:
                    await message.channel.send(help_text)
                else:
                    print(help_text)

            elif not hasattr(args, 'parser'):
                print("No parser found for the command.")

            if hasattr(args, 'func'):
                await args.func(args)
                return

