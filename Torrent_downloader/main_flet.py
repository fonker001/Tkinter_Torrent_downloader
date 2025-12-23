import flet as ft
import requests
import threading
import base64
from datetime import datetime
from typing import Dict, List


class SimpleYTSBrowser:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "YTS Browser"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.window.width = 1100
        self.page.window.height = 700
        
        # Data storage
        self.movies = {}
        self.selected_torrent = None
        
        # Build UI
        self.build_ui()
    
    def build_ui(self):
        # Search controls
        self.search_box = ft.TextField(hint_text="Enter movie name...", expand=True)
        self.search_btn = ft.ElevatedButton("Search", on_click=self.on_search)
        
        # Status
        self.status = ft.Text("Ready")
        
        # Movies list
        self.movie_list = ft.ListView(expand=True, spacing=5, padding=10)
        
        # Movie details
        self.title = ft.Text("", size=20, weight="bold")
        self.poster = ft.Image(width=150, height=225, border_radius=10)
        self.details = ft.Column([
            ft.Text("Year: -"),
            ft.Text("Rating: -/10"),
            ft.Text("Runtime: - mins"),
            ft.Text("Genres: -")
        ], spacing=5)
        
        self.summary = ft.Text("", selectable=True)
        
        # Torrents
        self.torrents_view = ft.Column(scroll=ft.ScrollMode.AUTO, height=150)
        
        # Download button
        self.download_btn = ft.ElevatedButton(
            "Download Selected Torrent",
            on_click=self.on_download,
            disabled=True
        )
        
        # Layout
        left_panel = ft.Container(
            content=ft.Column([
                ft.Text("Movies", size=16, weight="bold"),
                self.movie_list
            ]),
            width=300,
            border=ft.border.all(1),
            border_radius=5,
            padding=10
        )
        
        right_panel = ft.Column([
            ft.Row([self.poster, ft.Column([self.title, self.details], expand=True)], spacing=20),
            ft.Divider(),
            ft.Text("Summary", size=14, weight="bold"),
            ft.Container(self.summary, padding=10, border=ft.border.all(1), border_radius=5),
            ft.Text("Available Qualities", size=14, weight="bold"),
            ft.Container(self.torrents_view, border=ft.border.all(1), border_radius=5, padding=5),
            self.download_btn
        ], spacing=15, expand=True)
        
        self.page.add(
            ft.Column([
                ft.Row([self.search_box, self.search_btn]),
                self.status,
                ft.Row([left_panel, right_panel], expand=True)
            ], expand=True)
        )
    
    def on_search(self, e):
        query = self.search_box.value.strip()
        if not query:
            self.status.value = "Please enter a search term"
            self.page.update()
            return
        
        self.search_btn.disabled = True
        self.status.value = f"Searching for '{query}'..."
        self.page.update()
        
        threading.Thread(target=self.do_search, args=(query,), daemon=True).start()
    
    def do_search(self, query):
        try:
            url = f"https://yts.lt/api/v2/list_movies.json?query_term={query}"
            response = requests.get(url, timeout=15)
            data = response.json()
            
            # Clear old results
            self.movie_list.controls.clear()
            self.movies.clear()
            
            movies = data.get("data", {}).get("movies", [])
            if not movies:
                self.status.value = "No results found"
            else:
                for movie in movies:
                    movie_id = movie["id"]
                    self.movies[movie_id] = movie
                    
                    # Create list item
                    item = ft.ListTile(
                        title=ft.Text(movie["title"][:40]),
                        subtitle=ft.Text(f"{movie['year']} | Rating: {movie['rating']}/10"),
                        on_click=lambda e, mid=movie_id: self.show_movie(mid)
                    )
                    self.movie_list.controls.append(item)
                
                self.status.value = f"Found {len(movies)} movies"
            
        except Exception as err:
            self.status.value = f"Error: {err}"
        finally:
            self.search_btn.disabled = False
            self.page.update()
    
    def show_movie(self, movie_id):
        movie = self.movies.get(movie_id)
        if not movie:
            return
        
        # Update basic info
        self.title.value = movie["title"]
        self.details.controls[0].value = f"Year: {movie['year']}"
        self.details.controls[1].value = f"Rating: {movie['rating']}/10"
        self.details.controls[2].value = f"Runtime: {movie['runtime']} mins"
        self.details.controls[3].value = f"Genres: {', '.join(movie['genres'])}"
        self.summary.value = movie.get("description_full", "No summary available")
        
        # Clear torrents
        self.torrents_view.controls.clear()
        self.selected_torrent = None
        self.download_btn.disabled = True
        
        # Add torrents
        for torrent in movie.get("torrents", []):
            date_str = datetime.fromtimestamp(torrent["date_uploaded_unix"]).strftime("%Y-%m-%d")
            
            torrent_btn = ft.TextButton(
                content=ft.Row([
                    ft.Text(f"Quality: {torrent['quality']}", width=80),
                    ft.Text(f"Size: {torrent['size']}", width=100),
                    ft.Text(f"Seeds: {torrent['seeds']}", width=60),
                    ft.Text(f"Date: {date_str}", width=100)
                ]),
                on_click=lambda e, t=torrent: self.select_torrent(t)
            )
            self.torrents_view.controls.append(torrent_btn)
        
        # Load poster
        if movie.get("medium_cover_image"):
            threading.Thread(target=self.load_poster, args=(movie["medium_cover_image"],), daemon=True).start()
        
        self.status.value = f"Loaded: {movie['title']}"
        self.page.update()
    
    def load_poster(self, url):
        try:
            response = requests.get(url, timeout=10)
            img_base64 = base64.b64encode(response.content).decode()
            self.poster.src_base64 = img_base64
            self.page.update()
        except:
            self.poster.src = ""
            self.page.update()
    
    def select_torrent(self, torrent):
        self.selected_torrent = torrent
        self.download_btn.disabled = False
        self.status.value = f"Selected: {torrent['quality']} ({torrent['size']})"
        self.page.update()
    
    def on_download(self, e):
        if not self.selected_torrent:
            return
        
        # Simple download without file dialog for compatibility
        try:
            response = requests.get(self.selected_torrent["url"], timeout=15)
            filename = f"{self.title.value} - {self.selected_torrent['quality']}.torrent"
            
            with open(filename, "wb") as f:
                f.write(response.content)
            
            self.status.value = f"Downloaded: {filename}"
        except Exception as err:
            self.status.value = f"Download error: {err}"
        
        self.page.update()


# Run the app
ft.app(target=SimpleYTSBrowser)