
import json
import argparse

from .airport_db import AirportDB
from .discord_bot import DiscordCopilote
from .meteo_france import MeteoFrance
from .utils import Plane

def main():
    print("Hello, Discord Copilote!")

    parser = argparse.ArgumentParser(description="Discord Copilote Bot")
    parser.add_argument("--config", type=str, default="config.json", help="Path to the configuration file")
    args = parser.parse_args() 

    with open(args.config, "r") as f:
        config = json.load(f)

    meteo_france = MeteoFrance(api_key=config["meteo-france"]["apikey"])
    airport_db = AirportDB(api_token=config["airport-db"]["apiToken"])

    plane_list = []
    if "planes" in config:
        for plane_config in config["planes"]:
            new_plane = Plane(plane_config)
            plane_list.append(new_plane)


    client = DiscordCopilote()
    client.set_airport_db(airport_db)
    client.set_meteo_france(meteo_france)
    client.set_planes(plane_list)
    client.run(config["discord"]["apikey"])

