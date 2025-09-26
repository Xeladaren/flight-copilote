import math

class GeoPos:
    def __init__(self, latitude: float, longitude: float, altitude: float = 0.0):
        self.lat = latitude
        self.lon = longitude
        self.alt = altitude

    def __repr__(self):
        return f"GeoPos({self.lat}, {self.lon}, {self.alt})"
    
    def __format__(self, format_spec):
        
        if format_spec == "deg": # Format : DD.DDDDDD [NS] DD.DDDDDD [EW]
            lat_dir = "N" if self.lat >= 0 else "S"
            lon_dir = "E" if self.lon >= 0 else "W"
            return f"{abs(self.lat):.6f} {lat_dir} {abs(self.lon):.6f} {lon_dir}"
        elif format_spec == "min": # Format : DD° MM.MMM' [NS] DD° MM.MMM' [EW]
            # Latitude
            lat_deg = int(abs(self.lat))
            lat_min = (abs(self.lat) - lat_deg) * 60
            lat_dir = "N" if self.lat >= 0 else "S"
            # Longitude
            lon_deg = int(abs(self.lon))
            lon_min = (abs(self.lon) - lon_deg) * 60
            lon_dir = "E" if self.lon >= 0 else "W"
            # Format
            return f"{lat_deg}° {lat_min:06.3f}' {lat_dir} {lon_deg}° {lon_min:06.3f}' {lon_dir}"
        elif format_spec == "sec": # Format : DD° MM' SS.S'' [NS] DD° MM' SS.S'' [EW]
            # Latitude
            lat_deg = int(abs(self.lat))
            lat_min_full = (abs(self.lat) - lat_deg) * 60
            lat_min = int(lat_min_full)
            lat_sec = (lat_min_full - lat_min) * 60
            lat_dir = "N" if self.lat >= 0 else "S"
            # Longitude
            lon_deg = int(abs(self.lon))
            lon_min_full = (abs(self.lon) - lon_deg) * 60
            lon_min = int(lon_min_full)
            lon_sec = (lon_min_full - lon_min) * 60
            lon_dir = "E" if self.lon >= 0 else "W"
            # Format
            return (f"{lat_deg}° {lat_min}' {lat_sec:.1f}\" {lat_dir} "
                    f"{lon_deg}° {lon_min}' {lon_sec:.1f}\" {lon_dir}")
        else: # Format [-]xx.xxxxxx [-]yy.yyyyyy
            return f"{self.lat:.6} {self.lon:.6}"

    def __str__(self):
        return f"{self:deg}"
    
    def latitude(self):
        return self.lat
    
    def longitude(self):
        return self.lon
    
    def altitude(self, unit="m"):
        if unit == "m":
            return self.alt
        elif unit == "ft":
            return self.alt / 0.3048
        else:
            raise ValueError("Unsupported unit. Use 'm' or 'ft'.")
    
    def distance_to(self, other: "GeoPos", unit="m") -> float:
        from math import radians, sin, cos, sqrt, atan2

        # Rayon moyen de la Terre en mètres
        R = 6371000

        # Conversion des coordonnées en radians
        lat1_rad = radians(self.lat)
        lon1_rad = radians(self.lon)
        lat2_rad = radians(other.lat)
        lon2_rad = radians(other.lon)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        # Distance au sol en mètres
        ground_distance = R * c

        # Prise en compte de l'altitude
        delta_alt = other.alt - self.alt
        total_distance = sqrt(ground_distance**2 + delta_alt**2)

        if unit == "km":
            return total_distance / 1000
        elif unit == "nm":
            return total_distance / 1852
        else:  # mètres
            return total_distance
    
    def heading_to(self, other: "GeoPos") -> float:
        from math import radians, degrees, sin, cos, atan2

        lat1_rad = radians(self.lat)
        lon1_rad = radians(self.lon)
        lat2_rad = radians(other.lat)
        lon2_rad = radians(other.lon)

        dlon = lon2_rad - lon1_rad

        x = sin(dlon) * cos(lat2_rad)
        y = cos(lat1_rad) * sin(lat2_rad) - (sin(lat1_rad) * cos(lat2_rad) * cos(dlon))

        initial_bearing = atan2(x, y)
        initial_bearing = degrees(initial_bearing)
        compass_bearing = (initial_bearing + 360) % 360

        return compass_bearing