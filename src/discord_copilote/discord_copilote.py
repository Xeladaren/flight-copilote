
import json
from .airport_db import AirportDB
from .discord_bot import DiscordCopilote

def main():
    print("Hello, Discord Copilote!")

    with open("config.json", "r") as f:
        config = json.load(f)

    airport_db = AirportDB(api_token=config["airport-db"]["apiToken"])

    # airport = airport_db.get_airport("LFOU")
    # print(airport)
    # print(airport.to_markdown())

    client = DiscordCopilote()
    client.set_airport_db(airport_db)
    client.run(config["discord"]["apikey"])

