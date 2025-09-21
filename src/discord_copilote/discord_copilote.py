
import json
import argparse

from .airport_db import AirportDB
from .discord_bot import DiscordCopilote
from .meteo_france import MeteoFrance

def main():
    print("Hello, Discord Copilote!")

    parser = argparse.ArgumentParser(description="Discord Copilote Bot")
    parser.add_argument("--config", type=str, default="config.json", help="Path to the configuration file")
    args = parser.parse_args() 

    with open(args.config, "r") as f:
        config = json.load(f)

    meteo_france = MeteoFrance(api_key=config["meteo-france"]["apikey"])
    airport_db = AirportDB(api_token=config["airport-db"]["apiToken"])


    # airport = airport_db.get_airport("LFOU")
    # print(airport)
    # print(airport.to_markdown())

    client = DiscordCopilote()
    client.set_airport_db(airport_db)
    client.set_meteo_france(meteo_france)
    client.run(config["discord"]["apikey"])

