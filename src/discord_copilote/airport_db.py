
import http.client
import json
import urllib.parse
import re
import datetime
import sys
import time

from .metar import metar_get
from .utils import GeoPos

class AirportDBRunway:
    def __init__(self, data: dict):
        self.data = data

    def __str__(self):
        return json.dumps(self.data, indent=4)
    
    def length(self, unit="m") -> float:
        if unit == "m":
            try:
                return float(self.data.get('length_ft', 0)) * 0.3048
            except:
                return float('nan')
        elif unit == "ft": 
            try:
                return float(self.data.get('length_ft', 0))
            except:
                return float('nan')
        else:
            raise ValueError("Unsupported unit. Use 'ft' or 'm'.")
    
    def width(self, unit="m") -> float:
        if unit == "m":
            try:
                return float(self.data.get('width_ft', 0)) * 0.3048
            except:
                return float('nan')
        elif unit == "ft": 
            try:
                return float(self.data.get('width_ft', 0))
            except:
                return float('nan')
        else:
            raise ValueError("Unsupported unit. Use 'ft' or 'm'.")
    
    def surface(self) -> str:
        try:
            return self.data.get('surface', 'N/A')
        except:
            return 'N/A'
    
    def closed(self) -> bool:
        if 'closed' in self.data and self.data['closed'] == "1":
            return True
        return False
    
    def lighted(self) -> bool:
        if 'lighted' in self.data and self.data['lighted'] == "1":
            return True
        return False
        
    def le_ident(self) -> str:
        return self.data.get('le_ident', 'N/A')
    
    def le_elevation(self, unit="ft") -> float:
        if unit == "m":
            try:
                return float(self.data.get('le_elevation_ft', 0)) * 0.3048
            except:
                return float('nan')
        elif unit == "ft": 
            try:
                return float(self.data.get('le_elevation_ft', 0))
            except:
                return float('nan')
        else:
            raise ValueError("Unsupported unit. Use 'ft' or 'm'.")

    def le_heading(self) -> float:
        try:
            return float(self.data.get('le_heading_degT', 0))
        except:
            return float('nan')
    
    def he_ident(self) -> str:
        return self.data.get('he_ident', 'N/A')
    
    def he_elevation(self, unit="ft") -> float:
        if unit == "m":
            try:
                return float(self.data.get('he_elevation_ft', 0)) * 0.3048
            except:
                return float('nan')
        elif unit == "ft": 
            try:
                return float(self.data.get('he_elevation_ft', 0))
            except:
                return float('nan')
        else:
            raise ValueError("Unsupported unit. Use 'ft' or 'm'.")
        
    def he_heading(self) -> float:
        try:
            return float(self.data.get('he_heading_degT', 0))   
        except:
            return float('nan')
    
    def to_markdown(self, indent=0, indent_str="  ") -> str:

        md  = indent_str*indent + f"- **{self.data.get('le_ident', 'N/A')}/{self.data.get('he_ident', 'N/A')}** - {self.length():.0f} m x {self.width():.0f} m, Surface: {self.surface()}"
        if self.closed():
            md += " (Closed)"
        if self.lighted():
            md += " (Lighted)"
        md += "\n"
        md += indent_str*(indent+1) + f"- **{self.le_ident()}** Elev: {self.le_elevation():.0f} ft, Heading: {self.le_heading():03.0f}° \n"
        md += indent_str*(indent+1) + f"- **{self.he_ident()}** Elev: {self.he_elevation():.0f} ft, Heading: {self.he_heading():03.0f}° \n"

        return md
    
class AirportDBFrequency:
    def __init__(self, data: dict):
        self.data = data

    def __str__(self):
        return json.dumps(self.data, indent=4)
    
    def type(self) -> str:
        return self.data.get('type', 'N/A')
    
    def description(self) -> str:
        return self.data.get('description', 'N/A')
    
    def frequency_mhz(self) -> float:
        return float(self.data.get('frequency_mhz', 0))
    
    def to_markdown(self, indent=0, indent_str="  ") -> str:
        md = indent_str*indent + f"- **{self.type()}**: {self.description()} - {self.frequency_mhz():.3f} MHz\n"
        return md

class AirportDBAirport:
    def __init__(self, data: dict):
        self.data = data

        rw_data = data.get('runways', [])
        if rw_data == None:
            rw_data = []
        self.runways = [AirportDBRunway(rw) for rw in rw_data]
        
        freqs_data = data.get('freqs', [])
        if freqs_data == None:
            freqs_data = []
        self.freqs = [AirportDBFrequency(fr) for fr in freqs_data]

        lat = float(self.data.get('latitude_deg', 0))
        lon = float(self.data.get('longitude_deg', 0))
        alt = float(self.data.get('elevation_ft', 0)) * 0.3048

        self.pos = GeoPos(lat, lon, alt)

    def __str__(self):
        return json.dumps(self.data, indent=4)
    
    def name(self) -> str:
        return self.data.get('name', 'Unknown Airport')
    
    def city(self) -> str:
        return self.data.get('municipality', 'N/A')
    
    def iata_code(self) -> str:
        return self.data.get('iata_code', 'N/A')
    
    def icao_code(self) -> str:
        return self.data.get('icao_code', 'N/A')
    
    def position(self) -> GeoPos:
        return self.pos
    
    def elevation(self, unit="ft") -> float:
        return self.pos.altitude(unit=unit)
        
    def country(self) -> str:
        if "country" in self.data and "name" in self.data['country']:
            return self.data['country']['name']
        return "N/A"
    
    def region(self) -> str:
        if "region" in self.data and "name" in self.data['region']:
            return self.data['region']['name']
        return "N/A"
    
    def station_icao(self) -> str:
        if "station" in self.data and "icao_code" in self.data['station']:
            return self.data['station']['icao_code']
        return None
    
    def station_distance(self, unit="nm") -> float:
        if "station" in self.data and "distance" in self.data['station']:
            if unit == "km":
                return float(self.data['station']['distance']) * 1.852
            elif unit == "nm":
                return float(self.data['station']['distance'])
        return 0.0
    
    def distance_to(self, other: "AirportDBAirport", unit="nm") -> float:
        return self.pos.distance_to(other.pos, unit=unit)
    
    def heading_to(self, other: "AirportDBAirport") -> float:
        return self.pos.heading_to(other.pos)
    
    def to_markdown(self, meteo_france=None) -> str:
        md = f"# {self.name()} ({self.icao_code()})\n"

        md += f"- **Country**: {self.country()}\n"
        md += f"- **Region**: {self.region()}\n"
        md += f"- **City**: {self.city()}\n"
        md += f"- **IATA Code**: {self.iata_code()}\n"
        md += f"- **ICAO Code**: {self.icao_code()}\n"
        md += f"- **GeoPosition**: {self.pos:min} ({self.pos})\n"
        elev_ft = f"{self.elevation(unit="ft"):_.0f}".replace("_", " ")
        elev_m  = f"{self.elevation(unit="m" ):_.0f}".replace("_", " ")
        md += f"- **Elevation**: {elev_ft} ft ({elev_m} m)\n"

        md += "## Runways:\n"
        for rw in self.runways:
            md += rw.to_markdown(indent=1)

        md += "## Frequencies:\n"
        for freq in self.freqs:
            md += freq.to_markdown(indent=1)

        return md


class AirportDB:
    
    def __init__(self, api_token: str):
        self.api_token = api_token
        self._last_update = None
        self._airports = []
        self._runways = []
        self._frequencies = []
        self._navaids = []
        self._countries = []
        self._regions = []

    def _decode_line(self, line):
        line_out = []

        for elem in line:
            if '"' in elem:
                line_out.append(elem.replace('"', ''))
            elif elem.isdecimal():
                line_out.append(int(elem))
            elif re.match(r"[+-]?\d*\.\d+", elem):
                line_out.append(float(elem))
            elif elem == "":
                line_out.append(None)
            else:
                line_out.append(elem)
                
        return line_out
    
    def _update_db(self, force=False):
        need_update = force

        if not need_update:
            if self._last_update is None:
                need_update = True
            elif datetime.datetime.now() - self._last_update > datetime.timedelta(days=1):
                need_update = True
        
        if need_update:

            self._last_update = datetime.datetime.now()

            print(f"[{time.time():.3f}] Start update")

            self._airports    = self._update_csv(self._airports,    "Airports",    "/ourairports-data/airports.csv")
            self._runways     = self._update_csv(self._runways,     "Runways",     "/ourairports-data/runways.csv")
            self._frequencies = self._update_csv(self._frequencies, "Frequencies", "/ourairports-data/airport-frequencies.csv")
            self._navaids     = self._update_csv(self._navaids,     "Navaids",     "/ourairports-data/navaids.csv")
            self._countries   = self._update_csv(self._countries,   "Countries",   "/ourairports-data/countries.csv")
            self._regions     = self._update_csv(self._regions,     "Regions",   "/ourairports-data/regions.csv")

            print(f"[{time.time():.3f}] OK")

    def _update_csv(self, old_database, database_name, database_path):
        try:
            database = self._get_csv(database_path)
        except Exception as e:
            print(f"Fail to get {database_name} database: {str(e)}")
            return old_database
        else:
            print(f"[{time.time():.3f}] {database_name} update OK")
            return database

    def _get_csv(self, path):

        host = "davidmegginson.github.io"

        url = urllib.parse.urlunparse(("", "", path, "", "", ""))

        connect = http.client.HTTPSConnection(host)
        connect.request("GET", url)
        response = connect.getresponse()
        raw_data = response.read().decode()
        data_line = raw_data.split("\n")

        csv_data = []

        if len(data_line) > 1:
            headers = self._decode_line(data_line[0].split(","))

            for line in data_line[1:]:
                datas = self._decode_line(line.split(","))

                new_elem = {}
                for header, data in zip(headers, datas):
                    new_elem[header] = data

                if len(new_elem) == len(headers):
                    csv_data.append(new_elem)

        return csv_data

    def get_airport(self, value, key='id'):
        
        self._update_db()

        out_airport = None

        for airport in self._airports:
            if key in airport and type(airport[key]) == str and value.upper() == airport[key].upper():
                out_airport = airport.copy()
                id = out_airport['id']
                break

        print(f"Searching airport with {key}={value} -> Found: {out_airport is not None}")
        if not out_airport:
            raise Exception(f"Airport with {key}={value} not found")

        if out_airport:
            for runway in self._runways:
                if runway["airport_ref"] == id:
                    if not "runways" in out_airport:
                        out_airport["runways"] = []
                    out_airport["runways"].append(runway)
                    print(f"  Added runway {runway['le_ident']}/{runway['he_ident']}")

            for frequencie in self._frequencies:
                if frequencie["airport_ref"] == id:
                    if not "freqs" in out_airport:
                        out_airport["freqs"] = []
                    out_airport["freqs"].append(frequencie)

            for country in self._countries:
                if country['code'] == out_airport['iso_country']:
                    if not "country" in out_airport:
                        out_airport["country"] = country
                        break
            
            for region in self._regions:
                if region['code'] == out_airport['iso_region']:
                    if not "region" in out_airport:
                        out_airport["region"] = region
                        break


        return AirportDBAirport(out_airport)

    
