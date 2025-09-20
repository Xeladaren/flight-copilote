
import http.client
import json
import urllib.parse

from .metar import metar_get

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

        self.runways = [AirportDBRunway(rw) for rw in data.get('runways', [])]
        self.freqs = [AirportDBFrequency(fr) for fr in data.get('freqs', [])]

    def __str__(self):
        return json.dumps(self.data, indent=4)
    
    def city(self) -> str:
        return self.data.get('municipality', 'N/A')
    
    def iata_code(self) -> str:
        return self.data.get('iata_code', 'N/A')
    
    def icao_code(self) -> str:
        return self.data.get('icao_code', 'N/A')
    
    def position(self) -> tuple:
        return (float(self.data.get('latitude_deg', 0)), float(self.data.get('longitude_deg', 0)))
    
    def elevation(self, unit="ft") -> float:
        if unit == "m":
            return float(self.data.get('elevation_ft', 0)) * 0.3048
        elif unit == "ft": 
            return float(self.data.get('elevation_ft', 0))
        else:
            raise ValueError("Unsupported unit. Use 'ft' or 'm'.")
        
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
    
    def metar(self) -> str:

        station_icao = self.station_icao()
        if not station_icao:
            return None

        try:
            return metar_get(station_icao)
        except Exception as e:
            print(f"Error fetching METAR data for {station_icao}: {str(e)}")
            return None
    
    def to_markdown(self) -> str:
        md = f"# {self.data.get('name', 'Unknown Airport')} ({self.icao_code()})\n"

        md += f"- **Country**: {self.country()}\n"
        md += f"- **Region**: {self.region()}\n"
        md += f"- **City**: {self.city()}\n"
        md += f"- **IATA Code**: {self.iata_code()}\n"
        md += f"- **ICAO Code**: {self.icao_code()}\n"
        md += f"- **Position**: {self.position()[0]:.6f}, {self.position()[1]:.6f}\n"
        md += f"- **Elevation**: {self.elevation():.0f} ft\n"

        md += "## Runways:\n"
        for rw in self.runways:
            md += rw.to_markdown(indent=1)

        md += "## Frequencies:\n"
        for freq in self.freqs:
            md += freq.to_markdown(indent=1)

        metar_data = self.metar()
    
        if metar_data:
            md += "## METAR:\n"
            if self.station_distance() > 0:
                md += f"*Donnée METAR de la station {self.station_icao()} à {self.station_distance():.1f} nm*\n"
            md += f"```\n{metar_data}\n```\n"
        return md

class AirportDB:
    
    def __init__(self, api_token: str):
        self.api_token = api_token

    def get_airport(self, icao_airport_code: str) -> AirportDBAirport:

        host = "airportdb.io"
        path = f"/api/v1/airport/{icao_airport_code.upper()}"

        querry = {"apiToken": self.api_token}

        url = urllib.parse.urlunparse(("", "", path, "", urllib.parse.urlencode(querry), ""))

        connect = http.client.HTTPSConnection(host)
        connect.request("GET", url)
        response = connect.getresponse()

        if response.status != 200:
            raise Exception(f"Error fetching airport data: {response.status} {response.reason}")

        data = json.loads(response.read().decode())
        airport = AirportDBAirport(data)
        connect.close()

        # Placeholder for actual API call
        return airport
    
