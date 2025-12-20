
import discord
import argparse

from .metar import metar_get, metar_get_around


class DiscordCopilote(discord.Client):

    def __init__(self, **options):
        intents = discord.Intents.default()
        intents.message_content = True  # Nécessaire pour lire le contenu des messages
        self.airport_db = None
        self.meteo_france = None
        self.plane_list = []
        super().__init__(intents=intents, **options)

    def set_airport_db(self, airport_db):
        self.airport_db = airport_db

    def set_meteo_france(self, meteo_france):
        self.meteo_france = meteo_france

    def set_planes(self, plane_list):
        self.plane_list = plane_list

    def print_metar(self, icao_code):
        md = ""
        try:
            metar_data = metar_get(icao_code)
        except Exception as e:

            try:
                airport = self.airport_db.get_airport(icao_code, key="icao_code")
            except Exception as e:
                print(f"Fail to get airport : {str(e)}")
                return None

            try:
                metar_around = metar_get_around(airport.position(), distance=100000, max_count=3)

                if len(metar_around) > 0:
                    md += f"*Pas de donnée METAR pour {icao_code}. Voici les données des stations proches:*\n"
                    for metar_distance, metar_info in metar_around:
                        md += f"*À {metar_distance/1000:.1f} km*\n"
                        md += f"```\n{metar_info}\n```\n"
            except Exception as e:
                print(f"Fail to get aroud metars : {str(e)}")
                return None

            if self.meteo_france:
                try:
                    station, distance = self.meteo_france.get_closest_station(airport.position(), unit="nm")
                    observation = self.meteo_france.get_observation_6m(station)
                    if distance < 2:
                        md += f"*Données Meteo France de la station à proximité de {airport.icao_code()}*\n"
                        metar_data = observation.to_metar(airport_oaci_code=airport.icao_code())
                    else:
                        md += f"*Données Meteo France de la station {station.name} à {distance:.1f} nm de {airport.icao_code()}*\n"
                        metar_data = observation.to_metar(airport_oaci_code=airport.icao_code())
                    md += f"```\n{metar_data}\n```\n"
                except Exception as e:
                    print(f"Fail to get meteo france data : {str(e)}")
        else:
            md += f"```\n{metar_data}\n```\n"

        return md
        

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
                airport = self.airport_db.get_airport(icao_code, key="icao_code")
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

            metar_data = self.print_metar(icao_code)
            if metar_data:
                md = "## METAR pour " + icao_code + "\n"
                md += metar_data
                if md and args.channel:
                    await args.channel.send(md)
            

    async def cmd_nav(self, args):
        print(args)

        try:
            airport_departure = self.airport_db.get_airport(args.icao_departure, key="icao_code")
        except Exception as e:
            print(f"Fail to get departure airport : {str(e)}")
            if args.channel:
                await args.channel.send(f"Fail to get departure airport {args.icao_departure}")
            return

        try:
            airport_arrival = self.airport_db.get_airport(args.icao_arrival, key="icao_code")
        except Exception as e:
            print(f"Fail to get arrival airport : {str(e)}")
            if args.channel:
                await args.channel.send(f"Fail to get arrival airport {args.icao_arrival}")
            return
        
        md  = f"# Navigation {airport_departure.icao_code()} -> {airport_arrival.icao_code()}\n"
        md += f"- **Departure**: {airport_departure.name()}, {airport_departure.region()}, {airport_departure.country()}\n"
        md += f"- **Departure Position**: {airport_departure.position():min}\n"
        md += f"- **Arrival**: {airport_arrival.name()}, {airport_arrival.region()}, {airport_arrival.country()}\n"
        md += f"- **Arrival Position**: {airport_arrival.position():min}\n"
        distance = airport_departure.distance_to(airport_arrival, unit="nm")
        md += f"- **Distance**: {distance:.2f} nm\n"
        md += f"- **Heading**: {airport_departure.heading_to(airport_arrival):.0f} °\n"

        if len(self.plane_list) > 0:
            md += f"## Planes\n"
            for plane in self.plane_list:
                md += f"- {plane.nav_md(distance)}\n"

        if args.channel:
            await args.channel.send(md)

    async def on_message(self, message):
        
        if message.author == self.user:
            return
        
        # print(f'Message de {message.author}: {message.content}')
        # if message.mentions:
        #     print(f'Mentions: {message.mentions}')

        # print(message.channel, type(message.channel))

        if self.user in message.mentions or type(message.channel) == discord.channel.DMChannel:
            message_str = message.content.replace(f'<@{self.user.id}>', '').strip()

            parser = argparse.ArgumentParser(prog=f"<@{self.user.id}>", add_help=False, exit_on_error=False)
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

            parser_nav = subparsers.add_parser('nav', add_help=False, help='Get Nav information between to airport.')
            parser_nav.add_argument('icao_departure', help='ICAO airport code of departure')
            parser_nav.add_argument('icao_arrival', help='ICAO airport code of arrival')
            parser_nav.add_argument('--help', '-h', action='store_true', help='Show this help message and exit')
            parser_nav.set_defaults(channel=message.channel, func=self.cmd_nav, parser=parser_nav)
            
            try:
                args = parser.parse_args(message_str.split())
            except Exception as e:
                if message.channel:
                    await message.channel.send(str(e))
                print(f"fail to parse cmd: {str(e)}")
                return

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

