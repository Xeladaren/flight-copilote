
import urllib.parse
import http.client


def metar_get(icao_airport_code: str) -> str:

    host = "aviationweather.gov"
    path = "/api/data/metar"

    querry = {
        "ids": icao_airport_code.upper(),
        "format": "raw",
    }

    url = urllib.parse.urlunparse(("", "", path, "", urllib.parse.urlencode(querry), ""))

    connect = http.client.HTTPSConnection(host)
    connect.request("GET", url)
    response = connect.getresponse()
    data = response.read().decode()


    if response.status != 200:
        raise Exception(f"Error fetching airport data: {response.status} {response.reason}")

    connect.close()
    return data
