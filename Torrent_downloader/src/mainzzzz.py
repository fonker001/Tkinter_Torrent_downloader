import requests
import threading
from tkinter import Tk, StringVar, filedialog, messagebox, Text
from tkinter.ttk import Frame, Scrollbar
from ttkbootstrap import Style
from ttkbootstrap.widgets import Entry, Button, Treeview, Label, Progressbar
from PIL import Image, ImageTk
from io import BytesIO
from datetime import datetime


class YTSBrowser:
    def __init__(self, root):
        self.root = root
        self.root.title("YTS Torrent Browser")
        self.style = Style("darkly")
        self.root.geometry("900x700")
        self.movie_cache = {}
        self.setup_ui()
        self.poster_label.photo_ref = None  # To keep reference to the image
        
        # Add this in __init__:
        self.poster_image_ref = None

        # Update in load_poster_image:
        #self.poster_image_ref = poster_img  # Keep reference
        #self.poster_label.config(image=poster_img)


    def setup_ui(self):
        # Main container frame
        main_container = Frame(self.root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Search Frame at top
        search_frame = Frame(main_container)
        search_frame.pack(fill="x", pady=(0, 10))
        
        self.search_var = StringVar()
        search_entry = Entry(search_frame, textvariable=self.search_var, width=50)
        search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.search_btn = Button(search_frame, text="Search", command=self.start_search_thread)
        self.search_btn.pack(side="left")
        
        # Main Content Frame (movie list + details)
        content_frame = Frame(main_container)
        content_frame.pack(fill="both", expand=True)
        
        # Left panel: Movie list (40% width)
        list_frame = Frame(content_frame)
        list_frame.pack(side="left", fill="both", expand=False, padx=(0, 10))
        
        Label(list_frame, text="Movies", font=('Helvetica', 10, 'bold')).pack(anchor="w")
        
        tree_scroll = Scrollbar(list_frame)
        tree_scroll.pack(side="right", fill="y")
        
        self.tree = Treeview(
            list_frame, 
            columns=("Title", "Year", "Rating", "ID"), 
            show="headings", 
            height=25,
            yscrollcommand=tree_scroll.set
        )
        tree_scroll.config(command=self.tree.yview)
        
        # Configure columns
        self.tree.column("Title", width=220, anchor="w")
        self.tree.column("Year", width=60, anchor="center")
        self.tree.column("Rating", width=70, anchor="center")
        self.tree.column("ID", width=0, stretch=False)
        
        for col in ["Title", "Year", "Rating", "ID"]:
            self.tree.heading(col, text=col)
        
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.show_movie_details)
        
        # Right panel: Details (60% width)
        details_frame = Frame(content_frame)
        details_frame.pack(side="right", fill="both", expand=True)
        
        # Top section: Poster and basic info
        top_frame = Frame(details_frame)
        top_frame.pack(fill="x", pady=(0, 10))
        
        # Poster image (fixed width)
        self.poster_label = Label(top_frame, width=25)
        self.poster_label.pack(side="left", padx=(0, 10))
        
        # Text info (flexible width)
        info_frame = Frame(top_frame)
        info_frame.pack(side="left", fill="both", expand=True)
        
        self.title_label = Label(info_frame, text="", font=("Helvetica", 14, "bold"), wraplength=400)
        self.title_label.pack(anchor="w", pady=(0, 5))
        
        # Metadata grid
        self.meta_frame = Frame(info_frame)
        self.meta_frame.pack(anchor="w")
        
        # Create grid for metadata
        for i, (label, attr) in enumerate([
            ("Year:", "year_label"),
            ("Rating:", "rating_label"),
            ("Runtime:", "runtime_label"), 
            ("Genres:", "genre_label")
        ]):
            Label(self.meta_frame, text=label).grid(row=i, column=0, sticky="e", padx=(0, 5))
            label_widget = Label(self.meta_frame, text="")
            label_widget.grid(row=i, column=1, sticky="w")
            setattr(self, attr, label_widget)
        
        # Summary section
        summary_frame = Frame(details_frame)
        summary_frame.pack(fill="x", pady=(0, 10))
        
        Label(summary_frame, text="Summary:", font=('Helvetica', 10, 'bold')).pack(anchor="w")
        
        summary_container = Frame(summary_frame)
        summary_container.pack(fill="x")
        
        summary_scroll = Scrollbar(summary_container)
        summary_scroll.pack(side="right", fill="y")
        
        self.summary_text = Text(
            summary_container,
            wrap="word",
            height=5,
            yscrollcommand=summary_scroll.set,
            font=('Helvetica', 10)
        )
        summary_scroll.config(command=self.summary_text.yview)
        self.summary_text.pack(fill="x")
        
        # Quality section
        quality_frame = Frame(details_frame)
        quality_frame.pack(fill="x", pady=(0, 10))
        
        Label(quality_frame, text="Available Qualities", font=('Helvetica', 10, 'bold')).pack(anchor="w")
        
        quality_scroll = Scrollbar(quality_frame)
        quality_scroll.pack(side="right", fill="y")
        
        self.quality_tree = Treeview(
            quality_frame,
            columns=("Quality", "Size", "Type", "Seeds", "Date", "Torrent"),
            show="headings",
            height=5,
            yscrollcommand=quality_scroll.set
        )
        quality_scroll.config(command=self.quality_tree.yview)
        
        # Configure quality tree columns
        for col, width in [("Quality", 70), ("Size", 80), ("Type", 60), ("Seeds", 60), ("Date", 80)]:
            self.quality_tree.heading(col, text=col)
            self.quality_tree.column(col, width=width, anchor="center")
        self.quality_tree.column("Torrent", width=0, stretch=False)
        
        self.quality_tree.pack(fill="x")
        
        # Bottom controls
        bottom_frame = Frame(main_container)
        bottom_frame.pack(fill="x", pady=(10, 0))
        
        self.download_btn = Button(bottom_frame, text="Download .torrent", command=self.download_torrent, state="disabled")
        self.download_btn.pack(side="left", padx=(0, 10))
        
        self.spinner = Progressbar(bottom_frame, mode="indeterminate", length=200)
        self.spinner.pack(side="left", padx=(0, 10))
        self.spinner.stop()
        
        self.status_label = Label(bottom_frame, text="Ready", wraplength=600)
        self.status_label.pack(side="left", fill="x", expand=True)
        
        # Configure grid weights for resizing
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
    
    def start_search_thread(self):
        """Start search in a separate thread to prevent UI freezing"""
        query = self.search_var.get().strip()
        if not query:
            messagebox.showwarning("Input Required", "Please enter a search term.")
            return
        
        self.search_btn.config(state="disabled")
        self.status_label.config(text=f"Searching for: {query}...")
        self.spinner.start()
        
        threading.Thread(
            target=self.search_movies,
            args=(query,),
            daemon=True
        ).start()
    
    def search_movies(self, query):
        """Search movies from YTS API"""
        try:
            url = f"https://yts.mx/api/v2/list_movies.json?query_term={query.replace(' ', '+')}"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            self.root.after(0, self.clear_results)
            
            movies = data["data"].get("movies", [])
            if not movies:
                self.root.after(0, lambda: self.status_label.config(text="No results found."))
            else:
                # Cache movie data and populate treeview
                for movie in movies:
                    self.movie_cache[movie["id"]] = movie
                    self.root.after(0, self.add_movie_to_tree, movie)
                
                self.root.after(0, lambda: self.status_label.config(
                    text=f"Found {len(movies)} result(s). Double-click a movie for details."
                ))
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Connection error: {e}"
            self.root.after(0, lambda msg=error_msg: self.status_label.config(text=msg))
        except Exception as e:
            error_msg = f"An error occurred: {e}"
            self.root.after(0, lambda msg=error_msg: self.status_label.config(text=msg))
        finally:
            self.root.after(0, lambda: self.search_btn.config(state="normal"))
            self.root.after(0, self.spinner.stop)
    
    def add_movie_to_tree(self, movie):
        """Add a movie to the results treeview"""
        self.tree.insert("", "end", values=(
            movie["title"],
            movie["year"],
            f"{movie['rating']}/10",
            movie["id"]  # Hidden column
        ))
    
    def show_movie_details(self, event):
        """Show details for the selected movie"""
        selected = self.tree.item(self.tree.focus())["values"]
        if not selected or len(selected) < 4:
            return
        
        movie_id = selected[3]
        if movie_id not in self.movie_cache:
            return
        
        self.status_label.config(text="Loading movie details...")
        self.spinner.start()
        self.download_btn.config(state="disabled")
        
        # Load details in a separate thread
        threading.Thread(
            target=self.load_movie_details,
            args=(movie_id,),
            daemon=True
        ).start()
    
    def load_movie_details(self, movie_id):
        """Load and display movie details"""
        try:
            movie = self.movie_cache.get(movie_id)
            if not movie:
                raise ValueError("Movie data not found in cache")

            # Get all values safely
            title = movie.get("title", "N/A")
            year = str(movie.get("year", ""))
            rating = f"{movie.get('rating', 0)}/10"
            runtime = f"{movie.get('runtime', 0)} mins" if movie.get('runtime') else "N/A"
            genres = ", ".join(movie.get("genres", ["N/A"]))
            summary = movie.get("description_full", "No summary available.")

            # Update UI
            self.root.after(0, lambda: [
                self.clear_details(),
                self.title_label.config(text=title),
                self.year_label.config(text=year),
                self.rating_label.config(text=rating),
                self.runtime_label.config(text=runtime),
                self.genre_label.config(text=genres),
                self.summary_text.delete(1.0, "end"),  # Clear existing text
                self.summary_text.insert("end", summary),  # Insert new summary
                self.quality_tree.delete(*self.quality_tree.get_children())
            ])

            # Rest of the method remains the same...
            # Load torrents
            for t in movie.get("torrents", []):
                self.root.after(0, lambda t=t: self.add_torrent_to_tree(t))

            # Load poster image if available
            if movie.get("medium_cover_image"):
                self.root.after(0, lambda: threading.Thread(
                    target=self.load_poster_image,
                    args=(movie["medium_cover_image"],),
                    daemon=True
                ).start())

            # Final updates
            self.root.after(0, lambda: [
                self.status_label.config(
                    text=f"Loaded: {title} ({year}). {len(movie.get('torrents', []))} quality options available."
                ),
                self.download_btn.config(state="normal"),
                self.spinner.stop()
            ])

        except Exception as e:
            error_msg = f"Error loading details: {str(e)}"
            self.root.after(0, lambda: [
                self.status_label.config(text=error_msg),
                self.spinner.stop()
            ])

    def load_poster_image(self, image_url):
        """Load and display movie poster"""
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            if 'image' not in response.headers.get('Content-Type', ''):
                raise ValueError("URL did not return an image")
                
            img_data = response.content
            img = Image.open(BytesIO(img_data))
            
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            img = img.resize((180, 270))
            poster_img = ImageTk.PhotoImage(img)
            
            self.root.after(0, lambda: [
                self.poster_label.config(image=poster_img),
                setattr(self.poster_label, 'image', poster_img),
                setattr(self.poster_label, 'photo_ref', poster_img)  # Keep reference
            ])
        except Exception as e:
            error_msg = f"Image error: {str(e)}"  # Create the message first
            self.root.after(0, lambda msg=error_msg: [  # Capture the message in lambda
                self.poster_label.config(image="", text="No Image Available"),
                self.status_label.config(text=msg)
            ])
    
    def add_torrent_to_tree(self, torrent):
        """Add a torrent quality option to the treeview"""
        date_str = datetime.fromtimestamp(torrent["date_uploaded_unix"]).strftime("%Y-%m-%d")
        self.quality_tree.insert("", "end", values=(
            torrent["quality"],
            torrent["size"],
            torrent["type"].capitalize(),
            torrent["seeds"],
            date_str,
            torrent["url"]  # Hidden column
        ))
    
    def download_torrent(self):
        """Download selected torrent file"""
        selected = self.quality_tree.item(self.quality_tree.focus())["values"]
        if not selected or len(selected) < 6:
            messagebox.showwarning("Selection Required", "Please select a quality to download.")
            return
        
        torrent_url = selected[5]
        default_filename = f"{self.title_label.cget('text')} - {selected[0]}.torrent"
        
        filename = filedialog.asksaveasfilename(
            initialfile=default_filename,
            defaultextension=".torrent",
            filetypes=[("Torrent files", "*.torrent"), ("All files", "*.*")]
        )
        
        if filename:
            self.status_label.config(text=f"Downloading torrent file...")
            self.spinner.start()
            self.download_btn.config(state="disabled")
            
            threading.Thread(
                target=self.perform_download,
                args=(torrent_url, filename),
                daemon=True
            ).start()
    
    def perform_download(self, url, filename):
        """Perform the actual torrent download in a thread"""
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            with open(filename, "wb") as f:
                f.write(response.content)
            
            self.root.after(0, lambda: self.status_label.config(text=f"Successfully saved: {filename}"))
        except requests.exceptions.RequestException as e:
            error_msg = f"Download failed: {e}"
            self.root.after(0, lambda msg=error_msg: self.status_label.config(text=msg))
        except Exception as e:
            error_msg = f"An error occurred: {e}"
            self.root.after(0, lambda msg=error_msg: self.status_label.config(text=msg))
        finally:
            self.root.after(0, self.spinner.stop)
            self.root.after(0, lambda: self.download_btn.config(state="normal"))
    
    def clear_results(self):
        """Clear all search results"""
        self.tree.delete(*self.tree.get_children())
        self.clear_details()
    
    def clear_details(self):
        """Clear movie details display"""
        self.title_label.config(text="")
        self.year_label.config(text="")
        self.rating_label.config(text="")
        self.runtime_label.config(text="")
        self.genre_label.config(text="")
        self.summary_text.delete(1.0, "end")  # Clear the Text widget
        self.poster_label.config(image="", text="No Image Selected")
        self.quality_tree.delete(*self.quality_tree.get_children())

if __name__ == "__main__":
    root = Tk()
    app = YTSBrowser(root)
    root.mainloop()