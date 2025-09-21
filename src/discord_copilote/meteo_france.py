
import os.path
import http.client
import urllib.parse
import json
import datetime

class MeteoFranceStation:
    def __init__(self, geo_id_insee, name, latitude, longitude, altitude):
        self.geo_id_insee = geo_id_insee
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude

    def __str__(self):
        return f"{self.name} ({self.geo_id_insee}) - {self.latitude:.4f},{self.longitude:.4f} Alt {self.altitude}m"
    
    def get_distance(self, latitude, longitude, unit="km"):
        # Haversine formula to calculate distance between two lat/lon points in km
        from math import radians, sin, cos, sqrt, atan2

        R = 6371.0  # Earth radius in km

        lat1 = radians(self.latitude)
        lon1 = radians(self.longitude)
        lat2 = radians(latitude)
        lon2 = radians(longitude)

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = R * c
        if unit == "m":
            distance *= 1000
        elif unit == "nm":
            distance /= 1.852

        return distance

class MeteoFranceObservation:
    def __init__(self, data: dict, station: MeteoFranceStation = None):
        self.data = data
        self.station = station

    def __str__(self):
        return json.dumps(self.data, indent=4, default=str)
    
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
    
    def get_closest_station(self, latitude, longitude):
        stations = self.get_station_list()
        if not stations:
            return None, 0.0

        closest_station = min(stations, key=lambda station: station.get_distance(latitude, longitude))
        return closest_station, closest_station.get_distance(latitude, longitude, unit="km")

    def get_observation_6m(self, station: MeteoFranceStation) -> MeteoFranceObservation:
        
        raw_data = self._get_data("station/infrahoraire-6m", query={"id_station": station.geo_id_insee, "format": "json"})
        data = json.loads(raw_data)

        if not data:
            raise Exception("Aucune donnée reçue pour l'observation.")
        return MeteoFranceObservation(data[0], station=station)