import requests
from datetime import datetime

class YTSAPI:
    BASE_URL = "https://yts.mx/api/v2"
    
    def search_movies(self, query):
        url = f"{self.BASE_URL}/list_movies.json?query_term={query.replace(' ', '+')}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data["data"].get("movies", [])
    
    def download_torrent(self, url, filename):
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        with open(filename, "wb") as f:
            f.write(response.content)