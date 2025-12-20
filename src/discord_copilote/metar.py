
import urllib.parse
import http.client
import json

from .utils import GeoPos

def geo_bbox(pos: GeoPos, distance_m):
    """
    Renvoie un bbox centré sur une position géographique, taille en mètres.
    :param center_lat: Latitude du centre (degrés)
    :param center_lon: Longitude du centre (degrés)
    :param size_m: Distance autour du point (float)
    :return: (min_lat, min_lon, max_lat, max_lon)
    """
    # 1 degré de latitude ≈ 111 320 m
    delta_lat = (distance_m) / 111320

    # 1 degré de longitude dépend de la latitude
    from math import cos, radians
    delta_lon = (distance_m) / (111320 * cos(radians(pos.lat)))

    min_lat = pos.lat - delta_lat
    max_lat = pos.lat + delta_lat
    min_lon = pos.lon - delta_lon
    max_lon = pos.lon + delta_lon
    return (min_lat, min_lon, max_lat, max_lon)

def metar_get(icao_airport_code: str) -> str:

    host = "aviationweather.gov"
    path = "/api/data/metar"

    querry = {
        "ids": icao_airport_code.upper(),
        "format": "raw",
        "taf": "true",
    }

    url = urllib.parse.urlunparse(("", "", path, "", urllib.parse.urlencode(querry), ""))

    connect = http.client.HTTPSConnection(host)
    connect.request("GET", url)
    response = connect.getresponse()
    data = response.read().decode()
    # print("METAR GET Response Status:", response.status)
    # print("METAR Data:", data)
    connect.close()

    if response.status != 200:
        raise Exception(f"Error fetching airport data: {response.status} {response.reason}")

    return data

def metar_get_around(pos: GeoPos, distance: float, max_count=None):

    host = "aviationweather.gov"
    path = "/api/data/metar"
    bbox = geo_bbox(pos, distance)

    querry = {
        "bbox": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
        "format": "json",
        "taf": "true",
        "hours": 0
    }

    url = urllib.parse.urlunparse(("", "", path, "", urllib.parse.urlencode(querry), ""))

    connect = http.client.HTTPSConnection(host)
    connect.request("GET", url)
    response = connect.getresponse()
    raw_data = response.read().decode()
        

    if response.status != 200:
        raise Exception(f"Error fetching airport data: {response.status} {response.reason}")

    if len(raw_data) < 2:
        return []

    connect.close()

    datas = json.loads(raw_data)

    # print("METAR Around Data:", json.dumps(datas, indent=4))

    metar_list = []
    for data in datas:
        data_pos   = GeoPos(data['lat'], data['lon'], data['elev'])
        data_metar = data['rawOb']

        if 'rawTaf' in data:
            data_taf = data['rawTaf']
            data_metar += "\n" + data_taf
        data_metar = data_metar.replace("TEMPO", "\n  TEMPO")
        data_metar = data_metar.replace("BECMG", "\n  BECMG")
        data_metar = data_metar.replace("PROB", "\n  PROB")

        metar = (pos.distance_to(data_pos), data_metar)
        metar_list.append(metar)

    metar_list.sort(key=lambda tup: tup[0])

    if max_count and len(metar_list) > max_count:
        return metar_list[:max_count]
    else:
        return metar_list