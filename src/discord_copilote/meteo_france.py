
import os.path
import http.client
import urllib.parse
import json
import datetime
import math

from .utils import GeoPos

class MeteoFranceStation:
    def __init__(self, geo_id_insee: str, name: str, latitude: float, longitude: float, altitude: float):
        self.geo_id_insee = geo_id_insee
        self.name = name
        self.pos = GeoPos(latitude, longitude, altitude=altitude)

    def __str__(self):
        return f"{self.name} ({self.geo_id_insee}) - {self.pos.latitude():.4f},{self.pos.longitude():.4f} Alt {self.pos.altitude()}m"
    
    def get_distance(self, other_pos: GeoPos, unit="nm"):
        return self.pos.distance_to(other_pos, unit=unit)

class MeteoFranceObservation:
    def __init__(self, data: dict, station: MeteoFranceStation = None):
        self.data = data
        self.station = station

    def __str__(self):
        return json.dumps(self.data, indent=4, default=str)
    
    def to_markdown(self) -> str:

        md = ""

        if self.data["pmer"] is not None:
            qnh_hpa = int(round(self.data["pmer"] / 100))
            md += f"- **QNH**: {qnh_hpa} hPa\n"

        if self.data["t"] is not None:
            t_c = int(round(self.data["t"] - 273.15))
            md += f"- **Temperature**: {t_c}°C\n"

        if self.data["td"] is not None:
            td_c = int(round(self.data["td"] - 273.15))
            md += f"- **Dew Point**: {td_c}°C\n"

        if self.data["u"] is not None:
            humidity = int(round(self.data["u"]))
            md += f"- **Humidity**: {humidity}%\n"

        if self.data["ff"] is not None:
            ff_kts = int(round(self.data["ff"] * (3600 / 1852)))
            md += f"- **Wind**: {ff_kts} kts"
            if self.data["dd"] is not None:
                dd = int(self.data["dd"])
                md += f" {dd}°"
            md += "\n"

        if self.data["fxi10"] is not None:
            fxi10_kts = int(round(self.data["fxi10"] * (3600 / 1852)))
            md += f"- **Gusts**: {fxi10_kts} kts"
            if self.data["dxi10"] is not None:
                dxi10 = int(self.data["dxi10"])
                md += f" {dxi10}°"
            md += "\n"

        if self.data["rr_per"] is not None:
            rrr_1h = self.data["rr_per"] * 10
            md += f"- **Precipitation**: {rrr_1h} mm/h\n"

        if self.data["vv"] is not None:
            md += f"- **Visibility**: {int(self.data['vv'])/1000:.2f} km\n"

        return md

    def preferred_runway(self, runways: list[int]) -> int:
        """
        Determine the preferred runway based on the current wind conditions.
        
        :param runways: A list of runway headings in degrees
        :type runways: list[int]
        :return: The preferred runway heading
        :rtype: int
        """

        if self.data['ff'] is None or self.data['dd'] is None:
            return runways[0]

        ff_kts = int(round(self.data['ff'] * (3600 / 1852)))
        dd = int(self.data['dd'])

        best_runway = runways[0]
        best_headwind = -9999

        best_index = 0
        index = 0

        for runway in runways:
            wind_angle = (dd - runway + 360) % 360
            if wind_angle > 180:
                wind_angle -= 360

            headwind = int(round(ff_kts * math.cos(math.radians(wind_angle))))

            if headwind > best_headwind:
                best_headwind = headwind
                best_runway = runway
                best_index = index

            index += 1

        return best_index, best_runway

    def runway_wind(self, runway_heading: int) -> tuple[int, int]:
        """
        Calculate the lateral wind component for a given runway heading.
        
        :param runway_heading: The runway heading in degrees
        :type runway_heading: int
        :return: A tuple containing the front wind component in kts, the lateral wind component in kts and the wind direction relative to the runway (left/right)
        :rtype: tuple[int, int, str]
        """

        if self.data['ff'] is None or self.data['dd'] is None:
            return 0, "N/A"

        ff_kts = int(round(self.data['ff'] * (3600 / 1852)))
        dd = int(self.data['dd'])

        wind_angle = (dd - runway_heading + 360) % 360

        if wind_angle > 180:
            wind_angle -= 360

        lateral_wind = int(round(ff_kts * abs(math.sin(math.radians(wind_angle)))))
        front_wind = int(round(ff_kts * math.cos(math.radians(wind_angle))))

        if wind_angle < 0:
            direction = "left"
        elif wind_angle > 0:
            direction = "right"
        else:
            direction = "headwind"

        return front_wind, lateral_wind, direction
    
    def to_metar(self, airport_oaci_code: str = None) -> str:

        if 'validity_time' in self.data and self.data['validity_time'] is not None:
            validity_time = datetime.datetime.fromisoformat(self.data['validity_time'])
        else:
            validity_time = datetime.datetime.now(datetime.timezone.utc)

        if airport_oaci_code is None:
            airport_oaci_code = self.station.name

        metar = f"METAR! {airport_oaci_code} {validity_time.day:02d}{validity_time.hour:02d}{validity_time.minute:02d}Z AUTO "

        if 'ff' in self.data and self.data['ff'] is not None:
            ff_kts = int(round(self.data['ff'] * (3600 / 1852)))
            if 'dd' in self.data and self.data['dd'] is not None:
                dd = int(self.data['dd'])
            else:
                dd = 0
            if ff_kts < 1:
                metar += "00000KT"
            elif ff_kts <= 3:
                metar += f"VRB{ff_kts:02d}KT "
            else:
                metar += f"{dd:03d}{ff_kts:02d}"
                if 'fxi10' in self.data and self.data['fxi10'] is not None:
                    fxi10_kts = int(round(self.data['fxi10'] * (3600 / 1852)))
                    if fxi10_kts >= ff_kts + 5:
                        metar += f"G{fxi10_kts:02d}KT "
                    else:
                        metar += "KT "

                if 'dxi10' in self.data and self.data['dxi10'] is not None:
                    dxi10 = int(self.data['dxi10'])
                    if abs(dd - dxi10) >= 10:
                        metar += f"{min(dd, dxi10):03d}V{max(dd, dxi10):03d} "
        else:
            metar += "/////KT "    

        if 'vv' in self.data and self.data['vv'] is not None:
            vv_m = int(self.data['vv'])
            if vv_m < 9999:
                metar += f"{vv_m:04d} "
            else:
                metar += "9999 "

        if 'rr_per' in self.data and self.data['rr_per'] is not None:
            rrr_6m = self.data['rr_per']
            if rrr_6m >= 0.1:
                if rrr_6m < 1:
                    metar += "DZ "
                elif rrr_6m < 2.5:
                    metar += "-RA "
                elif rrr_6m < 7.6:
                    metar += "RA "
                elif rrr_6m < 50:
                    metar += "+RA "
                else:
                    metar += "XXRA "

        if 't' in self.data and self.data['t'] is not None:
            t_c = int(round(self.data['t'] - 273.15))
            if t_c < 0:
                metar += f"M{abs(t_c):02d}/"
            else:
                metar += f"{t_c:02d}/"
        else:
            metar += "??/"

        if 'td' in self.data and self.data['td'] is not None:
            td_c = int(round(self.data['td'] - 273.15))
            if td_c < 0:
                metar += f"M{abs(td_c):02d} "
            else:
                metar += f"{td_c:02d} "
        else:
            metar += "?? "

        if 'pmer' in self.data and self.data['pmer'] is not None:
            qnh_hpa = int(round(self.data['pmer'] / 100))
            metar += f"Q{qnh_hpa:04d} ="
        else:
            metar += f"Q//// ="

        return metar

class MeteoFrance:
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.stations = None

    def _get_data(self, path, query={}):
        host = "public-api.meteofrance.fr"
        url_path = os.path.join("/public/DPObs/v1", path)

        headers = {
            "apikey": self.api_key,
            "accept": "*/*"
        }

        url = urllib.parse.urlunparse(("", "", url_path, "", urllib.parse.urlencode(query), ""))

        connect = http.client.HTTPSConnection(host)
        connect.request("GET", url, headers=headers)
        response = connect.getresponse()

        # print(response.status, response.reason)

        if response.status == 200:
            data = response.read()
            connect.close()
        else:
            connect.close()
            raise Exception(f"Erreur HTTP {response.status} {response.reason}")
        
        return data

    def get_station_list(self):

        if self.stations is None:
            try:
                raw_data = self._get_data("liste-stations")
            except Exception as e:
                print(f"Erreur lors de la récupération de la liste des stations: {str(e)}")
                return []

            csv_lines = raw_data.decode('utf-8').splitlines()

            if len(csv_lines) < 2:
                print("Aucune donnée reçue pour la liste des stations.")
                return []

            header = csv_lines[0].split(';')

            if not all(field in header for field in ["Id_station", "Nom_usuel", "Latitude", "Longitude", "Altitude"]):
                raise ValueError("Le format des données de la station a changé. Champs attendus manquants.")

            self.stations = []

            for station in csv_lines[1:]:
                fields = station.split(';')

                geo_id_insee = fields[header.index("Id_station")]
                name = fields[header.index("Nom_usuel")]
                latitude = float(fields[header.index("Latitude")])
                longitude = float(fields[header.index("Longitude")])
                altitude = int(fields[header.index("Altitude")])

                self.stations.append(MeteoFranceStation(geo_id_insee, name, latitude, longitude, altitude))

        return self.stations
    
    def get_closest_station(self, pos: GeoPos, unit="nm") -> tuple[MeteoFranceStation, float]:
        stations = self.get_station_list()
        if not stations:
            return None, 0.0

        closest_station = min(stations, key=lambda station: station.get_distance(pos))
        return closest_station, closest_station.get_distance(pos, unit=unit)

    def get_observation_6m(self, station: MeteoFranceStation) -> MeteoFranceObservation:
        
        raw_data = self._get_data("station/infrahoraire-6m", query={"id_station": station.geo_id_insee, "format": "json"})
        data = json.loads(raw_data)

        if not data:
            raise Exception("Aucune donnée reçue pour l'observation.")
        return MeteoFranceObservation(data[0], station=station)