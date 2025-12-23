# Update yts_api.py
import requests
from datetime import datetime

class YTSAPI:
    BASE_URL = "https://yts.lt/api/v2"
    
    def search_movies(self, query):
        url = f"{self.BASE_URL}/list_movies.json?query_term={query.replace(' ', '+')}"
        print(f"API DEBUG: Calling URL: {url}")
        
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        print(f"API DEBUG: Response status: {data.get('status', 'unknown')}")
        print(f"API DEBUG: Movies found: {len(data['data'].get('movies', []))}")
        
        movies = data["data"].get("movies", [])
        
        # Enhance movies with additional details
        enhanced_movies = []
        for movie in movies:
            try:
                enhanced = self.get_movie_details(movie['id'])
                if enhanced:
                    enhanced_movies.append(enhanced)
                else:
                    enhanced_movies.append(movie)
            except:
                enhanced_movies.append(movie)
        
        return enhanced_movies
    
    def get_movie_details(self, movie_id):
        """Get detailed movie information including full description"""
        url = f"{self.BASE_URL}/movie_details.json?movie_id={movie_id}&with_images=false&with_cast=true"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['status'] == 'ok' and 'movie' in data['data']:
                return data['data']['movie']
        except:
            pass
        
        return None
    
    def download_torrent(self, url, filename):
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        with open(filename, "wb") as f:
            f.write(response.content)