import threading
from tkinter import messagebox, filedialog
from tkinter.ttk import Frame
from ttkbootstrap import Style
from ttkbootstrap.widgets import Button, Label, Progressbar

from src.core.yts_api import YTSAPI
from src.core.update_manager import UpdateManager
from src.gui.components import SearchFrame, MovieList, MovieDetails, QualityList

class YTSBrowser:
    def __init__(self, root):
        self.root = root
        self.root.title("YTS Torrent Browser")
        self.style = Style("darkly")
        self.root.geometry("900x700")
        
        self.movie_cache = {}
        self.yts_api = YTSAPI()
        self.update_manager = UpdateManager(root, self.update_status)
        
        self.setup_ui()
        
        # Check for updates on startup
        threading.Thread(target=self.update_manager.check_for_updates, args=(True,), daemon=True).start()

    def setup_ui(self):
        # Main container
        main_container = Frame(self.root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Top menu bar
        menu_frame = Frame(main_container)
        menu_frame.pack(fill="x", pady=(0, 10))
        
        # Update button
        self.update_btn = Button(menu_frame, text="Check for Updates", 
                                command=self.check_for_updates_manual, width=20)
        self.update_btn.pack(side="right", padx=(5, 0))
        
        # Search component
        self.search_frame = SearchFrame(menu_frame, self.start_search_thread)
        self.search_frame.pack(side="left", fill="x", expand=True)
        
        # Content area
        content_frame = Frame(main_container)
        content_frame.pack(fill="both", expand=True)
        
        # Movie list (left)
        self.movie_list = MovieList(content_frame, self.show_movie_details)
        self.movie_list.pack(side="left", fill="both", expand=False, padx=(0, 10))
        
        # Movie details (right)
        self.movie_details = MovieDetails(content_frame)
        self.movie_details.pack(side="right", fill="both", expand=True)
        
        # Bottom controls
        bottom_frame = Frame(main_container)
        bottom_frame.pack(fill="x", pady=(10, 0))
        
        self.download_btn = Button(bottom_frame, text="Download .torrent", 
                                  command=self.download_torrent, state="disabled")
        self.download_btn.pack(side="left", padx=(0, 10))
        
        self.spinner = Progressbar(bottom_frame, mode="indeterminate", length=200)
        self.spinner.pack(side="left", padx=(0, 10))
        self.spinner.stop()
        
        self.status_label = Label(bottom_frame, text="Ready", wraplength=600)
        self.status_label.pack(side="left", fill="x", expand=True)

    def check_for_updates_manual(self):
        self.update_btn.config(state="disabled")
        self.status_label.config(text="Checking for updates...")
        threading.Thread(target=self.update_manager.check_for_updates, daemon=True).start()

    def update_status(self, message):
        self.root.after(0, lambda: self.status_label.config(text=message))
        self.root.after(0, lambda: self.update_btn.config(state="normal"))

    def start_search_thread(self):
        query = self.search_frame.get_search_term()
        if not query:
            messagebox.showwarning("Input Required", "Please enter a search term.")
            return
        
        self.search_frame.disable_search()
        self.status_label.config(text=f"Searching for: {query}...")
        self.spinner.start()
        
        threading.Thread(target=self.search_movies, args=(query,), daemon=True).start()

    def search_movies(self, query):
        try:
            movies = self.yts_api.search_movies(query)
            self.root.after(0, self.clear_results)
            
            if not movies:
                self.root.after(0, lambda: self.status_label.config(text="No results found."))
            else:
                for movie in movies:
                    self.movie_cache[movie["id"]] = movie
                    self.root.after(0, self.movie_list.add_movie, movie)
                
                self.root.after(0, lambda: self.status_label.config(
                    text=f"Found {len(movies)} result(s). Select a movie for details."
                ))
                
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text=f"Error: {str(e)}"))
        finally:
            self.root.after(0, self.search_frame.enable_search)
            self.root.after(0, self.spinner.stop)

    def show_movie_details(self, movie_id):
        if movie_id not in self.movie_cache:
            return
            
        self.status_label.config(text="Loading movie details...")
        self.spinner.start()
        self.download_btn.config(state="disabled")
        
        threading.Thread(target=self.load_movie_details, args=(movie_id,), daemon=True).start()

    def load_movie_details(self, movie_id):
        try:
            movie = self.movie_cache[movie_id]
            self.root.after(0, lambda: self.movie_details.display_movie(movie))
            
            # Load poster
            if movie.get("medium_cover_image"):
                self.root.after(0, lambda: threading.Thread(
                    target=self.movie_details.load_poster,
                    args=(movie["medium_cover_image"],),
                    daemon=True
                ).start())
            
            self.root.after(0, lambda: [
                self.status_label.config(text=f"Loaded: {movie['title']} ({movie['year']})"),
                self.download_btn.config(state="normal"),
                self.spinner.stop()
            ])
            
        except Exception as e:
            self.root.after(0, lambda: [
                self.status_label.config(text=f"Error loading details: {str(e)}"),
                self.spinner.stop()
            ])

    def download_torrent(self):
        selected_torrent = self.movie_details.get_selected_torrent()
        if not selected_torrent:
            messagebox.showwarning("Selection Required", "Please select a quality to download.")
            return
        
        movie_title = self.movie_details.get_movie_title()
        default_filename = f"{movie_title} - {selected_torrent['quality']}.torrent"
        
        filename = filedialog.asksaveasfilename(
            initialfile=default_filename,
            defaultextension=".torrent",
            filetypes=[("Torrent files", "*.torrent"), ("All files", "*.*")]
        )
        
        if filename:
            self.status_label.config(text="Downloading torrent file...")
            self.spinner.start()
            self.download_btn.config(state="disabled")
            
            threading.Thread(
                target=self.perform_download,
                args=(selected_torrent['url'], filename),
                daemon=True
            ).start()

    def perform_download(self, url, filename):
        try:
            self.yts_api.download_torrent(url, filename)
            self.root.after(0, lambda: self.status_label.config(text=f"Successfully saved: {filename}"))
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text=f"Download failed: {str(e)}"))
        finally:
            self.root.after(0, self.spinner.stop)
            self.root.after(0, lambda: self.download_btn.config(state="normal"))

    def clear_results(self):
        self.movie_list.clear()
        self.movie_details.clear()