
import http.client
import http.cookies
import urllib.parse
import datetime

class AeroWeb:

    HOST = "aviation.meteo.fr"
    USER_AGENT = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0"
    PLACES = {
            "france": {"code": "fr/france", "levels": ["fl020"]},
            "euroc":  {"code": "fr/teuroc", "levels": ["fl050", "fl180", "fl340"]},
            "eur":    {"code": "uk/smpz_eur", "levels": [
                "fl050", "fl080", 
                "fl100", "fl140", "fl180", 
                "fl210", "fl240", "fl270", 
                "fl300", "fl320", "fl340", "fl360", "fl390", 
                "fl410", "fl450", "fl480", 
                "fl530"]},
            # Add more place codes as needed
        }

    def __init__(self, username: str, password_md5: str):
        self.username = username
        self.password_md5 = password_md5

        self.cookie_jar = None #http.cookies.SimpleCookie()
        self.http_session = None #http.client.HTTPSConnection(AeroWeb.HOST)

    def __str__(self):
        return f"AeroWeb(User: {self.username})"

    def _load_cookies(self, headers: list[tuple[str, str]]):
        for header, value in headers:
            if header.lower() == "set-cookie":
                self.cookie_jar.load(value)

    def _get_cookies(self) -> str:
        out_data = ""
        for key, morsel in self.cookie_jar.items():
            out_data += f"{key}={morsel.value}; "
        return out_data

    def _print_cookies(self):
        print("Current Cookies:")
        for key, morsel in self.cookie_jar.items():
            print(f"{key}: {morsel.value}")
        print("End of Cookies\n")

    def get_info(self):
        return f"User: {self.username}"
    
    def login(self):

        self.cookie_jar = http.cookies.SimpleCookie()
        self.http_session = http.client.HTTPSConnection(AeroWeb.HOST)

        headers = {
            "User-Agent": AeroWeb.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive"
        }

        self.http_session.request("GET", "/login.php", headers=headers)
        response = self.http_session.getresponse()

        if response.status != 200:
            raise Exception(f"Erreur HTTP {response.status} {response.reason}")
        
        data = response.read()
        # print(data.decode('utf-8', errors='ignore'))
        
        # print("Initial GET response headers:", response.getheaders())
        self._load_cookies(response.getheaders())
        # self._print_cookies()

        headers = {
            "User-Agent": AeroWeb.USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Origin": f"https://{AeroWeb.HOST}",
            "Referer": f"https://{AeroWeb.HOST}/login.php",
            "Cookie": self._get_cookies(),
            "Content-Type": "application/x-www-form-urlencoded"
        }
        # print("Login Headers:", headers)

        self.http_session.request("POST", "/ajax/login_valid.php",
            body=f"login={self.username}&password={self.password_md5}",
            headers=headers
        )
        response = self.http_session.getresponse()
        # print(response.status, response.reason)

        if response.status != 200:
            raise Exception(f"Erreur HTTP {response.status} {response.reason}")

        self._load_cookies(response.getheaders())
        # self._print_cookies()
        data = response.read().decode('utf-8', errors='ignore')
        if "ok" in data:
            print("Login successful")
        else:
            print("Login failed :", data)
            raise Exception("Login failed")
        
    def logout(self):
        if not self.http_session:
            return

        self.http_session.close()
        self.http_session = None
        self.cookie_jar = None
        
    def get_last_date(self) -> datetime.datetime:
        """
        Get the last available date for TEMSI/WINTEM images.
        The data is every 3 hours at 0, 3, 6, 9, 12, 15, 18, 21 UTC,
        available 2 hours before the hour.

        :return: Last available date
        :rtype: datetime.datetime
        """
        
        now = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(hours=2)
        hour = (now.hour // 3) * 3
        last_date = datetime.datetime(now.year, now.month, now.day, hour, 0, 0, tzinfo=datetime.timezone.utc)
        return last_date


    def get_places(self) -> list[str]:
        """
        Get the available place codes for TEMSI/WINTEM images.
        
        :return: A dictionary of place names and their codes
        :rtype: dict
        """
        return list(self.PLACES.keys())

    def get_place(self, name: str) -> dict:
        """
        Get the place code for TEMSI/WINTEM images.
        
        :param name: The name of the place (e.g., "france", "teuroc")
        :type name: str
        :return: The place code
        :rtype: str
        """
        return self.PLACES.get(name.lower(), None)

    def get_temsi(self, date: datetime.datetime, place: str = "fr/france") -> bytes:
        """
        Get the TEMSI image for a specific date.
        
        :param date: The date for which to get the TEMSI image
        :type date: datetime.datetime
        :return: The TEMSI image data in bytes
        :rtype: bytes
        """

        image_type = f"sigwx/{place}"
        return self.get_image(date, image_type=image_type)

    def get_wintem(self, date: datetime.datetime, place: str = "fr/france", level: str = "fl020") -> bytes:
        """
        Get the WINTEM image for a specific date.
        
        :param date: The date for which to get the WINTEM image
        :type date: datetime.datetime
        :return: Description
        :rtype: bytes
        """

        image_type = f"wintemp/{place}/{level}"
        return self.get_image(date, image_type=image_type)


    def get_image(self, date: datetime.datetime, image_type: str) -> bytes:

        if not self.http_session:
            raise Exception("Not logged in")

        date_str = date.strftime("%Y%m%d%H%M%S")
        req_data = {
            "type": image_type,
            "date": date_str,
            "mode": "img"
        }

        # print("Cookie Jar:", self.cookie_jar.output(header="", sep="; "))
        headers = {
            "User-Agent": AeroWeb.USER_AGENT,
            "Accept": "image/avif,image/webp,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Referer": f"https://{AeroWeb.HOST}/accueil.php",
            "Cookie": self._get_cookies()
        }

        # print("Headers:", headers)

        query_string = urllib.parse.urlencode(req_data)
        self.http_session.request("GET", f"/affiche_image.php?{query_string}", headers=headers)
        response = self.http_session.getresponse()

        if response.status != 200:
            raise Exception(f"Erreur HTTP {response.status} {response.reason}")

        if response.getheader("Content-Type") != "image/png":
            raise Exception(f"Unexpected Content-Type: {response.getheader('Content-Type')}")

        self._load_cookies(response.getheaders())
        # self._print_cookies()

        return response.read()