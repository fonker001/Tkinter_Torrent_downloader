import threading
import json
import os
import sys

# CLEAN Tkinter imports - choose ONE approach
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, StringVar

# ttkbootstrap for themed widgets
from ttkbootstrap import Style
from ttkbootstrap.widgets import Button as TtkButton, Label as TtkLabel, Progressbar, Entry

# PIL for images
from PIL import Image, ImageTk


# Add the src directory to path for imports
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from core.yts_api import YTSAPI
    from core.update_manager import UpdateManager
    from utils.image_loader import load_image_from_url
    from core.semantic_search import YTSSemanticSearch
    from gui.components import SearchFrame, MovieList, MovieDetails, QualityList
except ImportError as e:
    print(f"Import error in app.py: {e}")
    # Try alternative import paths
    try:
        from src.core.yts_api import YTSAPI
        from src.core.update_manager import UpdateManager
        from utils.image_loader import load_image_from_url
        from src.gui.components import SearchFrame, MovieList, MovieDetails, QualityList
        from src.core.semantic_search import YTSSemanticSearch
    except ImportError:
        from .components import SearchFrame, MovieList, MovieDetails, QualityList
        from .core.semantic_search import YTSSemanticSearch
        # For core modules, we'll need to handle them differently



class YTSBrowser:
    def __init__(self, root):
        self.root = root
        self.root.title("YTS Torrent Browser - Find Your Next Movie")
        self.style = Style("superhero")
        self.root.minsize(1000,600)
        self.root.resizable(True, True)
        self.setup_custom_theme()
        self.root.configure(bg="#0a0e17")
        
        self.movie_cache = {}
        self.current_movies = []
        self.yts_api = YTSAPI()
        self.semantic_searcher = YTSSemanticSearch()
        self.update_manager = UpdateManager(root, self.update_status)
        self.setup_keyboard_shortcuts()
        self.bookmarks = self.load_bookmarks()
        self.setup_ui()
        
        # Check for updates on startu
        threading.Thread(target=self.update_manager.check_for_updates, args=(True,), daemon=True).start()

    def setup_ui(self):
        # Main container - Use ttk.Frame since we're using ttkbootstrap
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Store main_container as instance variable
        self.main_container = tk.Frame(self.root, bg=self.colors['background'])
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)  # Content area expands
                
        # Top menu bar
        menu_frame = tk.Frame(self.main_container, bg=self.colors['background'], height=50)
        menu_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        menu_frame.grid_propagate(False)  # Keep fixed height
                
        # LEFT SIDE: Search and sorting
        left_menu = tk.Frame(menu_frame, bg=self.colors['background'])
        left_menu.pack(side="left", fill="both", expand=True)
        
        # Search component - PASS COLORS
        self.search_frame = SearchFrame(left_menu, 
                                       self.start_search_thread,
                                       colors=self.colors)
        self.search_frame.pack(side="left", fill="x", expand=True)
        
        # Search type toggle
        search_type_frame = tk.Frame(left_menu, bg=self.colors['background'])
        search_type_frame.pack(side="left", padx=(0, 10))
        
        # Use ttkbootstrap Label
        tk.Label(search_type_frame, 
                text="Search type:",
                bg=self.colors['background'],
                fg=self.colors['text']).pack(side="left")
        
        self.search_type_var = StringVar(value="keyword")
        search_type_combo = ttk.Combobox(
            search_type_frame, 
            textvariable=self.search_type_var,
            values=["Keyword", "Describe Plot"],
            state="readonly",
            width=15
        )
        search_type_combo.pack(side="left", padx=(5, 0))
        
        # Add semantic search hint
        self.search_hint = TtkLabel(
            left_menu,
            text="🔍 Try: 'movies about hackers in virtual reality'",
            font=("Helvetica", 9)
        )
        self.search_hint.pack(side="left", padx=(10, 0))
        self.search_hint.pack_forget()
        
        # Bind search type change
        search_type_combo.bind('<<ComboboxSelected>>', self.on_search_type_changed)
        
        # Sorting frame
        sort_frame = ttk.Frame(left_menu)
        sort_frame.pack(side="left", padx=(20, 0))
        
        TtkLabel(sort_frame, text="Sort:").pack(side="left")
        
        self.sort_var = StringVar(value="Rating (High to Low)")
        sort_combo = ttk.Combobox(sort_frame, 
                                 textvariable=self.sort_var, 
                                 values=["Rating (High to Low)", "Year (Newest)", "Title (A-Z)"],
                                 state="readonly", 
                                 width=16)
        sort_combo.pack(side="left", padx=(5, 0))
        sort_combo.bind('<<ComboboxSelected>>', self.apply_sorting)
        
        # RIGHT SIDE: Buttons
        right_menu = ttk.Frame(menu_frame)
        right_menu.pack(side="right")
        
        # Use ttkbootstrap Button with style
        semantic_btn = TtkButton(right_menu, 
                               text="🧠 Semantic", 
                               command=self.show_semantic_info, 
                               width=12,
                               bootstyle="primary")  # Use bootstyle instead of style
        semantic_btn.pack(side="right", padx=(5, 0))
        
        # Bookmarks button
        self.bookmarks_btn = TtkButton(right_menu, 
                                     text="📚 Bookmarks", 
                                     command=self.show_bookmarks, 
                                     width=15)
        self.bookmarks_btn.pack(side="right", padx=(5, 0))
        
        # Update button
        self.update_btn = TtkButton(right_menu, 
                                  text="Check for Updates", 
                                  command=self.check_for_updates_manual, 
                                  width=20)
        self.update_btn.pack(side="right", padx=(5, 0))
        
        # Content area
        self.content_frame = tk.Frame(self.main_container, bg=self.colors['background'])
        self.content_frame.grid(row=1, column=0, sticky="nsew")
        
        # Configure content frame columns
        self.content_frame.grid_columnconfigure(0, weight=0)  # Movie list (fixed)
        self.content_frame.grid_columnconfigure(1, weight=1)  # Details (expands)
            
        # Movie list (left) - PASS COLORS
        # Movie list (left) - FIXED WIDTH
        self.movie_list = MovieList(self.content_frame, 
                                   self.show_movie_details,
                                   colors=self.colors)
        self.movie_list.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        
        # Movie details (right) - EXPANDS
        self.movie_details = MovieDetails(self.content_frame, colors=self.colors)
        self.movie_details.grid(row=0, column=1, sticky="nsew")
        
        # Bottom controls - FIXED HEIGHT
        bottom_frame = tk.Frame(self.main_container, 
                               bg=self.colors['background'], 
                               height=40)
        bottom_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        bottom_frame.grid_propagate(False)

        self.download_btn = tk.Button(bottom_frame, 
                                     text="⬇️ Download .torrent", 
                                     command=self.download_torrent, 
                                     state="disabled",
                                     bg=self.colors['primary'],
                                     fg='white',
                                     font=('Segoe UI', 10))
        self.download_btn.pack(side="left", padx=(0, 10))
            
        # Spinner in its own frame
        spinner_frame = tk.Frame(bottom_frame, bg=self.colors['background'])
        spinner_frame.pack(side="left", padx=(0, 15))
        
        self.spinner = ttk.Progressbar(spinner_frame, 
                                      mode="indeterminate", 
                                      length=120)
        self.spinner.pack(side="left")
        
        # Status label with dynamic wrapping
        self.status_label = tk.Label(bottom_frame, 
                                    text="🚀 Ready to search!", 
                                    bg=self.colors['background'],
                                    fg=self.colors['text'],
                                    wraplength=500,
                                    anchor="w",
                                    justify="left")
        self.status_label.pack(side="left", fill="x", expand=True, padx=(10, 0))
        
        # Force initial layout update
        self.root.update_idletasks()

    def setup_custom_theme(self):
        """Setup ttkbootstrap theme with custom colors"""
        # Use cyborg theme from ttkbootstrap
        self.style = Style(theme="cyborg")
        
        # Define colors for custom tk widgets (not ttk)
        self.colors = {
            'primary': '#00adb5',
            'secondary': '#393e46',
            'background': '#0a0e17',
            'surface': '#1a1f2e',
            'text': '#eeeeee',
            'text_secondary': '#a0aec0',
            'success': '#00d26a',
            'warning': '#ff9d00',
            'error': '#ff4757',
            'highlight': '#6c5ce7',
        }
        
        # Configure ttkbootstrap styles
        self.style.configure('primary.TButton',
                            background=self.colors['primary'])
        
        # For root window background (if needed)
        self.root.configure(bg=self.colors['background'])


    # Add fade-in effect for movie cards
    def fade_in(widget, alpha=0):
        if alpha < 1:
            # Tkinter doesn't support opacity directly, but you can simulate
            widget.config(bg=self.blend_colors(alpha))
            widget.after(50, lambda: fade_in(widget, alpha + 0.1))

    def check_for_updates_manual(self):
        self.update_btn.config(state="disabled")
        self.status_label.config(text="Checking for updates...")
        threading.Thread(target=self.update_manager.check_for_updates, daemon=True).start()


    def setup_keyboard_shortcuts(self):
        """Set up keyboard shortcuts"""
        # Search - F5
        self.root.bind('<F5>', lambda e: self.start_search_thread())
        
        # Quick download - Ctrl+D
        self.root.bind('<Control-d>', lambda e: self.download_torrent() if self.download_btn['state'] == 'normal' else None)
        
        # Clear - Escape
        self.root.bind('<Escape>', lambda e: self.clear_results())
        
        # Focus search - Ctrl+F
        self.root.bind('<Control-f>', lambda e: self.search_frame.search_entry.focus())
        
        # Quit - Ctrl+Q
        self.root.bind('<Control-q>', lambda e: self.root.quit())


    def load_bookmarks(self):
        """Load bookmarks from file"""
        try:
            bookmarks_file = "bookmarks.json"
            if os.path.exists(bookmarks_file):
                with open(bookmarks_file, 'r') as f:
                    return json.load(f)
            return []
        except:
            return []

    def save_bookmarks(self):
        """Save bookmarks to file"""
        try:
            with open("bookmarks.json", 'w') as f:
                json.dump(self.bookmarks, f)
        except:
            pass

    def toggle_bookmark(self):
        """Toggle bookmark for current movie"""
        if hasattr(self, 'current_movie_id') and self.current_movie_id:
            movie_id = self.current_movie_id
            movie = self.movie_cache.get(movie_id)
            
            if movie_id in self.bookmarks:
                self.bookmarks.remove(movie_id)
                self.bookmark_btn.config(text="⭐ Bookmark")
                self.show_status("Bookmark removed", "info")
            else:
                self.bookmarks.append(movie_id)
                self.bookmark_btn.config(text="✅ Bookmarked")
                self.show_status("Movie bookmarked!", "success")
            
            self.save_bookmarks()

    def show_bookmarks(self):
        """Show bookmarked movies"""
        bookmarked_movies = [self.movie_cache.get(mid) for mid in self.bookmarks if mid in self.movie_cache]
        bookmarked_movies = [m for m in bookmarked_movies if m]  # Remove None values
        
        if not bookmarked_movies:
            self.show_status("No bookmarks yet", "warning")
            return
        
        self.clear_results()
        for movie in bookmarked_movies:
            self.movie_list.add_movie(movie)  # FIXED: Use movie_list.add_movie instead of add_movie_to_tree
        self.show_status(f"Showing {len(bookmarked_movies)} bookmarks", "success")


    def show_status(self, message, message_type="info", duration=3000):
        """Show styled status messages"""
        colors = {
            "info": "#3498db",      # Blue
            "success": "#2ecc71",   # Green
            "warning": "#f39c12",   # Orange
            "error": "#e74c3c"      # Red
        }
        
        self.status_label.config(text=message, foreground=colors.get(message_type, "white"))
        
        # Auto-clear after duration
        if duration:
            self.root.after(duration, lambda: self.status_label.config(text="Ready", foreground="white"))

    def update_status(self, message):
        self.root.after(0, lambda: self.status_label.config(text=message))
        self.root.after(0, lambda: self.update_btn.config(state="normal"))

    def on_search_type_changed(self, event=None):
        """Update UI based on search type"""
        search_type = self.search_type_var.get().lower()
        
        if "describe" in search_type:
            # Show semantic search hint
            self.search_hint.pack(side="left", padx=(10, 0))
            self.search_frame.search_entry.config(height=3)
            self.search_frame.search_entry.delete("1.0", "end")
            self.search_frame.search_entry.insert(
                "1.0", 
                "Describe what you're looking for...\nExample: 'a mind-bending thriller about dreams'"
            )
        else:
            # Hide hint for keyword search
            self.search_hint.pack_forget()
            self.search_frame.search_entry.config(height=1)
            self.search_frame.search_entry.delete("1.0", "end")
 
    def start_search_thread(self):
        query = self.search_frame.get_search_term().strip()
        if not query:
            self.show_status("Please enter a search term", "warning")
            return
        
        # Check search type
        search_type = self.search_type_var.get().lower()
        
        self.search_frame.disable_search()
        
        if "describe" in search_type:
            # Semantic search
            self.show_status(f"Searching by description: {query[:50]}...", "info")
            threading.Thread(target=self.semantic_search, args=(query,), daemon=True).start()
        else:
            # Traditional keyword search
            self.show_status(f"Searching for: {query}...", "info")
            threading.Thread(target=self.search_movies, args=(query,), daemon=True).start()
        
        self.spinner.start()
    
    
    def semantic_search(self, query):
        """Perform semantic search"""
        try:
            print(f"DEBUG: Starting semantic search for: {query}")
            
            # Make sure we have movies in the cache to search
            if not self.movie_cache:
                print("DEBUG: No movies in cache, performing keyword search first")
                # Do a quick keyword search to populate cache
                movies = self.yts_api.search_movies("movie")
                if movies:
                    self.semantic_searcher.update_with_movies(movies)
            
            # Update semantic index with current cache
            if self.movie_cache:
                cached_movies = list(self.movie_cache.values())
                print(f"DEBUG: Updating semantic index with {len(cached_movies)} cached movies")
                self.semantic_searcher.update_with_movies(cached_movies)
            
            # Perform semantic search
            print(f"DEBUG: Performing semantic search...")
            results = self.semantic_searcher.search_by_description(
                query=query,
                top_n=20,
                min_similarity=0.2  # Lower threshold for better results
            )
            
            print(f"DEBUG: Semantic search returned {len(results)} results")
            
            # Extract just the movie dictionaries from results
            semantic_movies = []
            for result in results:
                movie = result['movie']
                if movie:  # Make sure we have movie data
                    # Add similarity score to movie for display
                    movie['similarity_score'] = result['similarity_score']
                    movie['search_match_type'] = 'semantic'
                    semantic_movies.append(movie)
            
            # If no results from semantic search, fall back to keyword search
            if not semantic_movies:
                print("DEBUG: No semantic results, falling back to keyword search")
                self.root.after(0, lambda: [
                    self.show_status("No semantic matches found. Trying keyword search...", "warning"),
                    self.search_movies(query)  # Fall back to regular search
                ])
                return
            
            # Update UI
            self.root.after(0, lambda: self.process_semantic_results(semantic_movies, query))
                
        except Exception as e:
            print(f"Semantic search error: {e}")
            import traceback
            traceback.print_exc()
            self.root.after(0, lambda: [
                self.show_status(f"Semantic search error: {str(e)}", "error"),
                self.search_frame.enable_search(),
                self.spinner.stop()
            ])

    def process_semantic_results(self, movies, query):
        """Process and display semantic search results"""
        print(f"DEBUG: Processing {len(movies)} semantic movies")
        
        self.current_movies = movies
        
        if not movies:
            self.movie_list.clear()
            self.show_status("No similar movies found. Try a different description.", "warning")
        else:
            # Store in cache
            for movie in movies:
                movie_id = movie.get("id")
                if movie_id:
                    self.movie_cache[movie_id] = movie
            
            # Display results
            self.movie_list.clear()
            for movie in movies:
                # Enhance display with similarity score
                similarity = movie.get('similarity_score', 0)
                movie['display_title'] = f"{movie['title']} ({movie['year']}) - 🎯 {similarity:.1%} match"
                self.movie_list.add_movie(movie)
            
            self.show_status(f"Found {len(movies)} movies matching: '{query}'", "success")
        
        self.search_frame.enable_search()
        self.spinner.stop()
    
    def search_movies(self, query):
        """Original keyword search (unchanged except for cache update)"""
        try:
            print(f"DEBUG: Searching for: {query}")
            movies = self.yts_api.search_movies(query)
            print(f"DEBUG: Found {len(movies)} movies")
            
            # Update semantic search index with new results
            if movies:
                self.semantic_searcher.update_with_movies(movies)
            
            # Update the UI in the main thread
            self.root.after(0, lambda: self.process_search_results(movies))
                
        except Exception as e:
            print(f"DEBUG: Search error: {e}")
            self.root.after(0, lambda: self.show_status(f"Search error: {str(e)}", "error"))
            self.root.after(0, self.search_frame.enable_search)
            self.root.after(0, self.spinner.stop)
    
    def process_search_results(self, movies):
        """Updated to mark as keyword results"""
        print(f"DEBUG: Processing {len(movies)} movies in main thread")
        
        self.current_movies = movies
        
        if not movies:
            self.movie_list.clear()
            self.show_status("No results found", "warning")
        else:
            # Store movies in cache
            for movie in movies:
                movie['search_match_type'] = 'keyword'
                self.movie_cache[movie["id"]] = movie
            
            # Apply sorting
            self.apply_sorting()
            
            self.show_status(f"Found {len(movies)} movies", "success")
        
        self.search_frame.enable_search()
        self.spinner.stop()
    
    def apply_sorting(self):
        """Enhanced sorting to handle semantic search results"""
        if not self.current_movies:
            return
        
        sort_type = self.sort_var.get()
        
        # Check if we have semantic search results
        has_similarity = any('similarity_score' in movie for movie in self.current_movies)
        
        if has_similarity and "Similarity" not in sort_type:
            # Add similarity sort option if we have semantic results
            current_values = self.sort_combo['values']
            if "Similarity (Best Match)" not in current_values:
                self.sort_combo['values'] = tuple(list(current_values) + ["Similarity (Best Match)"])
        
        if sort_type == "Similarity (Best Match)":
            self.current_movies.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
        elif sort_type == "Rating (High to Low)":
            self.current_movies.sort(key=lambda x: x.get('rating', 0), reverse=True)
        elif sort_type == "Year (Newest)":
            self.current_movies.sort(key=lambda x: x.get('year', 0), reverse=True)
        elif sort_type == "Title (A-Z)":
            self.current_movies.sort(key=lambda x: x.get('title', '').lower())
        
        self.refresh_movie_list()
    
    # Add to your existing methods:
    def clear_semantic_cache(self):
        """Clear semantic search cache (call from a menu option)"""
        if messagebox.askyesno("Clear Cache", "Clear semantic search cache? This will reset learning but may fix search issues."):
            self.semantic_searcher.clear_cache()
            self.show_status("Semantic cache cleared", "success")


    def show_movie_details(self, movie_id):
        if movie_id not in self.movie_cache:
            return
            
        self.status_label.config(text="Loading movie details...")
        self.spinner.start()
        self.download_btn.config(state="disabled")
        
        threading.Thread(target=self.load_movie_details, args=(movie_id,), daemon=True).start()


    def show_semantic_info(self):
        """Show semantic search information dialog"""
        info = """
        🧠 Semantic Search Mode
        
        • Search by describing plots, themes, or feelings
        • Example: "mind-bending sci-fi about reality"
        • Example: "funny high school comedy from the 90s"
        • Example: "epic fantasy with dragons and magic"
        
        The system learns from your searches and improves over time.
        First search may be slower as it builds the index.
        
        💡 Tip: Be descriptive rather than using specific titles.
        """
        
        messagebox.showinfo("Semantic Search Help", info)

    def load_movie_details(self, movie_id):
        try:
            movie = self.movie_cache[movie_id]
            self.current_movie_id = movie_id
            
            # Update UI immediately with basic info
            self.root.after(0, lambda: [
                self.movie_details.display_movie(movie),
                self.show_status("Loading poster...", "info")
            ])
            
            # Update bookmark button
            is_bookmarked = movie_id in self.bookmarks
            self.root.after(0, lambda: self.movie_details.set_bookmark_state(is_bookmarked))
            
            # Load poster with progress indication
            if movie.get("medium_cover_image"):
                # Start spinner for image loading
                self.root.after(0, lambda: [
                    self.spinner.start(),
                    self.status_label.config(text="Loading poster image...")
                ])
                
                # Load image in background thread
                threading.Thread(
                    target=self.load_poster_with_progress,
                    args=(movie["medium_cover_image"],),
                    daemon=True
                ).start()
            else:
                # No image to load, stop spinner
                self.root.after(0, lambda: [
                    self.show_status(f"Loaded: {movie['title']} ({movie['year']})", "success"),
                    self.download_btn.config(state="normal"),
                    self.spinner.stop()
                ])
                
        except Exception as e:
            self.root.after(0, lambda: [
                self.show_status(f"Error loading details: {str(e)}", "error"),
                self.spinner.stop()
            ])

    def load_poster_with_progress(self, image_url):
        """Load poster image with progress indication"""
        try:
            # Load image using your helper
            pil_image = load_image_from_url(image_url, (180, 270))

            # Convert to Tkinter image inside the UI thread
            def update_ui():
                tkimage = ImageTk.PhotoImage(pil_image)

                # Update poster only
                self.movie_details.poster_label.config(image=tkimage, text="")
                self.movie_details.poster_label.image = tkimage
                self.movie_details.poster_image_ref = tkimage  # store only TK image

                # DO NOT SET PIL IMAGE HERE
                # DO NOT USE setattr for images

                # Status + UI
                self.show_status(
                    f"Loaded: {self.movie_cache.get(self.current_movie_id, {}).get('title', 'Movie')}",
                    "success"
                )

                self.download_btn.config(state="normal")
                self.spinner.stop()


            # Run UI update on main thread
            self.root.after(0, update_ui)

        except Exception as e:
            self.show_status("Image load failed", "error")
            self.spinner.stop()
            print("Poster Load Error:", e)

            
        except Exception as e:
            self.root.after(0, lambda: [
                self.movie_details.poster_label.config(image="", text="No Image Available"),
                self.show_status(f"Image load failed", "warning"),
                self.download_btn.config(state="normal"),
                self.spinner.stop()
            ])


    def add_sorting_features(self):
        # Add sorting options to your menu
        sort_frame = Frame(self.menu_frame)
        sort_frame.pack(side="left", padx=(20, 0))
        
        Label(sort_frame, text="Sort by:").pack(side="left")
        
        self.sort_var = StringVar(value="rating")
        sort_options = [("Rating", "rating"), ("Year", "year"), ("Title", "title")]
        
        for text, value in sort_options:
            Radiobutton(sort_frame, text=text, variable=self.sort_var, 
                       value=value, command=self.apply_sorting).pack(side="left", padx=(5, 0))

    def apply_sorting(self, event=None):
        """Apply sorting to current movies"""
        if not self.current_movies:
            print("DEBUG: No movies to sort - trying to use movies from movie_list")
            # Try to get movies from the displayed list as fallback
            return
        
        print(f"DEBUG: Sorting {len(self.current_movies)} movies")
        sort_type = self.sort_var.get()
        
        if sort_type == "Rating (High to Low)":
            self.current_movies.sort(key=lambda x: x.get('rating', 0), reverse=True)
        elif sort_type == "Year (Newest)":
            self.current_movies.sort(key=lambda x: x.get('year', 0), reverse=True)
        elif sort_type == "Title (A-Z)":
            self.current_movies.sort(key=lambda x: x.get('title', '').lower())
        
        # Refresh the display with sorted movies
        self.refresh_movie_list()

    def refresh_movie_list(self):
        """Refresh the movie list with current sort"""
        print(f"DEBUG: refresh_movie_list called with {len(self.current_movies)} movies")
        
        if not hasattr(self, 'movie_list'):
            print("DEBUG: movie_list attribute doesn't exist!")
            return
            
        print("DEBUG: Calling movie_list.clear()")
        self.movie_list.clear()
        
        for i, movie in enumerate(self.current_movies):
            print(f"DEBUG: Adding movie {i+1}: {movie['title']}")
            self.movie_list.add_movie(movie)
        
        print("DEBUG: refresh_movie_list completed")


    def search_movies(self, query):
        try:
            print(f"DEBUG: Searching for: {query}")
            movies = self.yts_api.search_movies(query)
            print(f"DEBUG: Found {len(movies)} movies")
            
            # Update the UI in the main thread
            self.root.after(0, lambda: self.process_search_results(movies))
                
        except Exception as e:
            print(f"DEBUG: Search error: {e}")
            self.root.after(0, lambda: self.show_status(f"Search error: {str(e)}", "error"))
            self.root.after(0, self.search_frame.enable_search)
            self.root.after(0, self.spinner.stop)

    def process_search_results(self, movies):
        print(f"DEBUG: Processing {len(movies)} movies in main thread")

        self.current_movies = movies

        if not movies:
            self.movie_list.clear()
            self.show_status("No results found", "warning")
        else:
            # Store movies in cache (no UI updates here)
            for movie in movies:
                self.movie_cache[movie["id"]] = movie

            # Sorting will call refresh_movie_list() once
            self.apply_sorting()

            self.show_status(f"Found {len(movies)} movies", "success")

        self.search_frame.enable_search()
        self.spinner.stop()


    def toggle_bookmark(self):
        """Toggle bookmark for current movie"""
        if hasattr(self, 'current_movie_id') and self.current_movie_id:
            movie_id = self.current_movie_id
            movie = self.movie_cache.get(movie_id)
            
            if movie_id in self.bookmarks:
                self.bookmarks.remove(movie_id)
                self.movie_details.set_bookmark_state(False)  # FIXED: Use movie_details method
                self.show_status("Bookmark removed", "info")
            else:
                self.bookmarks.append(movie_id)
                self.movie_details.set_bookmark_state(True)  # FIXED: Use movie_details method
                self.show_status("Movie bookmarked!", "success")
            
            self.save_bookmarks()


    def on_quality_select(self, event):
        """Handle quality selection"""
        # This enables the download button when a quality is selected
        selected = self.movie_details.get_selected_torrent()
        if selected:
            self.download_btn.config(state="normal")

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
        #self.tree.delete(*self.tree.get_children())
        self.current_movies = []