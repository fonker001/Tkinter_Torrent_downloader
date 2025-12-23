import threading
import requests
from io import BytesIO
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from tkinter import StringVar
from PIL import Image, ImageTk


class SearchFrame(tk.Frame):  # Use tk.Frame
    def __init__(self, parent, search_callback, colors=None):
        super().__init__(parent)
        
        # Use provided colors or default
        self.colors = colors or {
            'background': '#0a0e17',
            'surface': '#1a1f2e',
            'primary': '#00adb5',
            'text': '#eeeeee'
        }
        
        # Set background
        self.configure(bg=self.colors['background'])
        
        self.search_callback = search_callback
        
        # Create a container for the search bar
        search_container = tk.Frame(self, bg=self.colors['surface'])  # tk.Frame
        search_container.pack(fill="x", expand=True)
        
        # Search entry
        self.search_entry = tk.Text(search_container,  # tk.Text
                                   height=2,
                                   width=50,
                                   bg=self.colors['surface'],
                                   fg=self.colors['text'],
                                   insertbackground=self.colors['text'],
                                   font=('Segoe UI', 11))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=10)
        self.search_entry.bind('<Return>', lambda e: search_callback())
        
        # Search button
        self.search_btn = tk.Button(search_container,  # tk.Button
                                   text="Search",
                                   command=search_callback,
                                   bg=self.colors['primary'],
                                   fg='white',
                                   font=('Segoe UI', 10, 'bold'),
                                   cursor="hand2")
        self.search_btn.pack(side="right", padx=(0, 10), pady=10)
    
    def get_search_term(self):
        return self.search_entry.get("1.0", "end").strip()
    
    def disable_search(self):
        self.search_btn.config(state="disabled")
        self.search_entry.config(state="disabled")
    
    def enable_search(self):
        self.search_btn.config(state="normal")
        self.search_entry.config(state="normal")
    
    def clear_search(self):
        self.search_entry.delete("1.0", "end")


class MovieList(tk.Frame):  # Use tk.Frame
    def __init__(self, parent, selection_callback, colors=None):
        super().__init__(parent)
        
        self.colors = colors or {
            'background': '#0a0e17',
            'surface': '#1a1f2e',
            'primary': '#00adb5',
            'text': '#eeeeee',
            'text_secondary': '#a0aec0',
            'highlight': '#6c5ce7',
            'success': '#00d26a',
            'warning': '#ff9d00'
        }
        
        self.configure(bg=self.colors['background'])
        self.selection_callback = selection_callback
        self.image_cache = {}
        self.lazy_rows = []
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the movie list UI"""
        # Header with movie count
        self.header_frame = tk.Frame(self, bg=self.colors['background'])  # tk.Frame
        self.header_frame.pack(fill="x", pady=(0, 10))
        
        self.count_label = tk.Label(self.header_frame,  # tk.Label
                                   text="Movies (0)",
                                   font=('Segoe UI', 11, 'bold'),
                                   bg=self.colors['background'],
                                   fg=self.colors['text'])
        self.count_label.pack(side="left")
        
        # Modern scrollable canvas
        self.canvas = tk.Canvas(self,  # tk.Canvas
                               bg=self.colors['background'],
                               highlightthickness=0,
                               bd=0)
        self.scrollbar = tk.Scrollbar(self,  # tk.Scrollbar
                                     orient="vertical",
                                     command=self.canvas.yview,
                                     bg=self.colors['surface'])
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.inner = tk.Frame(self.canvas, bg=self.colors['background'])  # tk.Frame
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", 
                       lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self.check_visible_rows)
        
        # Smooth scrolling with mouse wheel
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)
    
    def on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def add_movie(self, movie):
        """Add a movie to the list"""
        self.add_movie_item(movie)
        self.update_count()
    
    def add_movie_item(self, movie):
        """Create and add a movie item card"""
        movie_id = movie.get("id")
        if not movie_id:
            return
        
        poster_url = movie.get("medium_cover_image") or movie.get("small_cover_image")
        
        # Modern movie card with hover effects
        card = tk.Frame(self.inner,  # tk.Frame
                       bg=self.colors['surface'],
                       relief="flat",
                       padx=12,
                       pady=10,
                       cursor="hand2")
        card.pack(fill="x", pady=3)
        
        # Add subtle border for semantic matches
        similarity = movie.get('similarity_score')
        search_type = movie.get('search_match_type', 'keyword')
        if similarity and search_type == 'semantic':
            card.config(highlightbackground=self.colors['highlight'],
                       highlightthickness=1)
        
        # Hover effects
        card.bind("<Enter>", lambda e, w=card: self.on_card_hover(w, True))
        card.bind("<Leave>", lambda e, w=card: self.on_card_hover(w, False))
        card.bind("<Button-1>", lambda e, mid=movie_id: self.selection_callback(mid))
        
        # Thumbnail container
        thumbnail_frame = tk.Frame(card, 
                                  bg=self.colors['surface'],
                                  width=100,   # Increased from 50
                                  height=150) # Increased from 70
        thumbnail_frame.pack(side="left", padx=(0, 15), pady=5)  # Added pady
        thumbnail_frame.pack_propagate(False)
        
        # Placeholder with loading animation
        img_label = tk.Label(thumbnail_frame,  # tk.Label
                           text="🎬",
                           font=('Segoe UI', 20),
                           bg=self.colors['surface'],
                           fg=self.colors['text_secondary'],
                           width=4,
                           height=6)
        img_label.pack()
        
        # Movie info container
        info_frame = tk.Frame(card, bg=self.colors['surface'])  # tk.Frame
        info_frame.pack(side="left", fill="both", expand=True)
        
        # Title with optional semantic match badge
        title_frame = tk.Frame(info_frame, bg=self.colors['surface'])  # tk.Frame
        title_frame.pack(fill="x", pady=(0, 5))
        
        title_text = movie.get("title", "Unknown Title")
        title_label = tk.Label(title_frame,  # tk.Label
                              text=title_text,
                              font=('Segoe UI', 12, 'bold'),
                              bg=self.colors['surface'],
                              fg=self.colors['text'],
                              anchor="w",
                              justify="left")
        title_label.pack(side="left")
        
        # Semantic match badge
        if similarity and search_type == 'semantic':
            match_percent = f"{similarity:.0%}"
            badge = tk.Label(title_frame,  # tk.Label
                           text=f" 🎯 {match_percent} match",
                           font=('Segoe UI', 9, 'bold'),
                           bg=self.colors['highlight'],
                           fg='white',
                           padx=6,
                           pady=2,
                           relief="flat")
            badge.pack(side="left", padx=(8, 0))
        
        # Metadata row
        meta_text = f"📅 {movie.get('year', 'N/A')}   ⭐ {movie.get('rating', 0)}/10"
        if movie.get('runtime'):
            meta_text += f"   ⏱️ {movie['runtime']} min"
        
        meta_label = tk.Label(info_frame,  # tk.Label
                             text=meta_text,
                             font=('Segoe UI', 10),
                             bg=self.colors['surface'],
                             fg=self.colors['text_secondary'],
                             anchor="w")
        meta_label.pack(fill="x", pady=(0, 5))
        
        # Genres as tags
        genres = movie.get('genres', [])
        if genres:
            genres_frame = tk.Frame(info_frame, bg=self.colors['surface'])  # tk.Frame
            genres_frame.pack(fill="x", pady=(0, 5))
            
            for genre in genres[:3]:  # Show max 3 genres
                tag = tk.Label(genres_frame,  # tk.Label
                             text=genre,
                             font=('Segoe UI', 8),
                             bg='#2d3748',
                             fg=self.colors['text_secondary'],
                             padx=6,
                             pady=2,
                             relief="flat")
                tag.pack(side="left", padx=(0, 5))
        
        # Quality badges if available
        if movie.get('torrents'):
            quality_frame = tk.Frame(info_frame, bg=self.colors['surface'])  # tk.Frame
            quality_frame.pack(fill="x")
            
            qualities = set(t['quality'] for t in movie['torrents'][:3])
            for quality in sorted(qualities):
                if quality in ['720p', '1080p', '2160p']:
                    color = self.colors['success'] if quality == '1080p' else self.colors['warning']
                    quality_badge = tk.Label(quality_frame,  # tk.Label
                                           text=f" {quality} ",
                                           font=('Segoe UI', 8, 'bold'),
                                           bg=color,
                                           fg='white',
                                           padx=4,
                                           pady=1,
                                           relief="flat")
                    quality_badge.pack(side="left", padx=(0, 5))
        
        # Store for lazy loading
        self.lazy_rows.append((card, movie_id, poster_url, img_label))
        self.check_visible_rows()
    
    def on_card_hover(self, widget, is_hover):
        """Handle card hover effects with safety check"""
        if not widget.winfo_exists():
            return
        
        target_bg = '#2a3142' if is_hover else self.colors['surface']
        widget.config(bg=target_bg)
        
        for child in widget.winfo_children():
            if child.winfo_exists():
                child.config(bg=target_bg)
    
    def update_count(self):
        """Update the movie count display"""
        count = len(self.inner.winfo_children())
        self.count_label.config(text=f"Movies ({count})")
    
    def clear(self):
        """Clear all movies from the list"""
        for widget in self.inner.winfo_children():
            widget.destroy()
        self.image_cache.clear()
        self.lazy_rows.clear()
        self.update_count()
    
    def check_visible_rows(self, event=None):
        """Check which rows are visible and load their thumbnails"""
        if not self.lazy_rows:
            return
        
        y1 = self.canvas.canvasy(0)
        y2 = y1 + self.canvas.winfo_height()
        
        for frame, movie_id, url, label in self.lazy_rows:
            fy = frame.winfo_y()
            fh = frame.winfo_height()
            if fy + fh >= y1 and fy <= y2:
                if movie_id not in self.image_cache and url:
                    self.load_thumbnail_async(movie_id, url, label)

    def load_thumbnail_async(self, movie_id, url, label_widget):
        """Load thumbnail with better sizing"""
        if not url:
            return
        
        def worker():
            try:
                response = requests.get(url, timeout=10, verify=True)
                img = Image.open(BytesIO(response.content))
                
                # LARGER thumbnail size
                target_width = 170
                target_height = 200
                
                # Maintain aspect ratio
                img_ratio = img.width / img.height
                
                # Calculate new dimensions preserving aspect ratio
                if img.width > img.height:
                    # Landscape image
                    new_width = target_width
                    new_height = int(target_width / img_ratio)
                else:
                    # Portrait image
                    new_height = target_height
                    new_width = int(target_height * img_ratio)
                
                # Resize with high quality
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Create canvas with target size
                final_img = Image.new('RGB', (target_width, target_height), 
                                    color=(45, 55, 72))  # Dark gray background
                
                # Center the image on the canvas
                x_offset = (target_width - new_width) // 2
                y_offset = (target_height - new_height) // 2
                final_img.paste(img, (x_offset, y_offset))
                
                tk_img = ImageTk.PhotoImage(final_img)
                self.image_cache[movie_id] = tk_img
                
                # Update on main thread - FIXED: Store reference properly
                def update_ui():
                    label_widget.config(
                        image=tk_img, 
                        text=""
                    )
                    # Store reference on the widget itself too
                    label_widget.image = tk_img
                
                self.after(0, update_ui)
                
            except Exception as e:
                print(f"Thumbnail load error for {movie_id}: {e}")
                # Keep the emoji placeholder
        
        # THIS MUST BE INSIDE THE METHOD!
        threading.Thread(target=worker, daemon=True).start()


class QualityList(ttk.Frame):  # Use ttk.Frame for Treeview compatibility
    def __init__(self, parent, colors=None):
        super().__init__(parent)
        
        self.colors = colors or {
            'background': '#0a0e17',
            'surface': '#1a1f2e',
            'primary': '#00adb5',
            'text': '#eeeeee',
            'text_secondary': '#a0aec0'
        }
        
        # Note: ttk.Frame doesn't support bg directly
        # You'll need to style it or use tk.Frame
        self.setup_treeview()

    def setup_treeview(self):
        style = ttk.Style()
        style.configure("Dark.Treeview",
                       background=self.colors['surface'],
                       foreground=self.colors['text'],
                       fieldbackground=self.colors['surface'],
                       rowheight=22)
        style.map("Dark.Treeview", 
                 background=[('selected', self.colors['primary'])], 
                 foreground=[('selected', 'white')])

        scroll = tk.Scrollbar(self)  # tk.Scrollbar
        scroll.pack(side="right", fill="y")
        
        self.tree = ttk.Treeview(self,  # ttk.Treeview
                                columns=("Quality","Size","Type","Seeds","Date","Torrent"),
                                show="headings", 
                                height=5, 
                                yscrollcommand=scroll.set, 
                                style="Dark.Treeview")
        scroll.config(command=self.tree.yview)

        for col, width in [("Quality",70),("Size",80),("Type",60),("Seeds",60),("Date",80)]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor="center")
        self.tree.column("Torrent", width=0, stretch=False)
        self.tree.pack(fill="x")

    def add_torrent(self, torrent):
        date_str = datetime.fromtimestamp(torrent["date_uploaded_unix"]).strftime("%Y-%m-%d")
        self.tree.insert("", "end", values=(torrent["quality"], torrent["size"],
                                           torrent["type"].capitalize(), torrent["seeds"],
                                           date_str, torrent["url"]))

    def get_selected_torrent(self):
        selected = self.tree.item(self.tree.focus())["values"]
        if selected and len(selected)>=6:
            return {"quality":selected[0], "size":selected[1], "type":selected[2],
                   "seeds":selected[3], "date":selected[4], "url":selected[5]}
        return None

    def clear(self):
        self.tree.delete(*self.tree.get_children())


class MovieDetails(tk.Frame):  # Use tk.Frame
    def __init__(self, parent, colors=None):
        super().__init__(parent)
        
        self.colors = colors or {
            'background': '#0a0e17',
            'surface': '#1a1f2e',
            'primary': '#00adb5',
            'success': '#00d26a',
            'text': '#eeeeee',
            'text_secondary': '#a0aec0'
        }
        
        self.configure(bg=self.colors['background'])
        self.poster_image_ref = None
        self.current_movie = None
        self.root = parent.winfo_toplevel()
        self.bookmark_callback = None
        self.download_callback = None
        self.root = parent.winfo_toplevel()
        self.setup_ui()
    
    def setup_ui(self):
        # Modern card-style container
        self.container = tk.Frame(self,  # tk.Frame
                                 bg=self.colors['surface'],
                                 relief="flat",
                                 padx=20,
                                 pady=20)
        self.container.pack(fill="both", expand=True)
        self.setup_movie_header()
        self.setup_summary_section()
        self.setup_quality_section()
        self.setup_action_buttons()
    
    def setup_movie_header(self):
        """Setup the movie poster and basic info section"""
        header_frame = tk.Frame(self.container, bg=self.colors['surface'])
        header_frame.pack(fill="x", pady=(0, 20))
        
        # Poster with shadow effect
        poster_shadow = tk.Frame(header_frame, 
                                bg='#000000',
                                padx=2,
                                pady=2)
        poster_shadow.pack(side="left", padx=(0, 20))
        
        self.poster_label = tk.Label(poster_shadow, 
                                    width=25,
                                    height=12,
                                    text="No Image",
                                    font=('Segoe UI', 10),
                                    bg=self.colors['surface'],
                                    fg=self.colors['text_secondary'],
                                    relief="flat")
        self.poster_label.pack()
        
        # Movie info section
        info_frame = tk.Frame(header_frame, bg=self.colors['surface'])
        info_frame.pack(side="left", fill="both", expand=True)
        
        # Title
        self.title_label = tk.Label(info_frame,
                                   text="Select a movie",
                                   font=('Segoe UI', 20, 'bold'),
                                   bg=self.colors['surface'],
                                   fg=self.colors['text'],
                                   wraplength=400,
                                   anchor="w",
                                   justify="left")
        self.title_label.pack(anchor="w", pady=(0, 10))
        
        # Metadata grid
        self.setup_metadata_grid(info_frame)

    def setup_metadata_grid(self, parent):
        """Setup the metadata grid (year, rating, runtime, etc.)"""
        grid_frame = tk.Frame(parent, bg=self.colors['surface'])
        grid_frame.pack(anchor="w", pady=(0, 15))
        
        self.metadata_labels = {}
        metadata_fields = [
            ("Year:", "year_label", "📅"),
            ("Rating:", "rating_label", "⭐"),
            ("Runtime:", "runtime_label", "⏱️"),
            ("Genres:", "genre_label", "🎭"),
            ("Language:", "language_label", "🌐"),
        ]
        
        for i, (label_text, key, icon) in enumerate(metadata_fields):
            row = i % 3
            col = i // 3 * 2
            
            # Icon
            icon_label = tk.Label(grid_frame,
                                text=icon,
                                font=('Segoe UI', 11),
                                bg=self.colors['surface'],
                                fg=self.colors['primary'])
            icon_label.grid(row=row, column=col, sticky="e", padx=(0, 5), pady=3)
            
            # Label
            lbl = tk.Label(grid_frame,
                         text=label_text,
                         font=('Segoe UI', 10),
                         bg=self.colors['surface'],
                         fg=self.colors['text_secondary'])
            lbl.grid(row=row, column=col+1, sticky="w", padx=(0, 10))
            
            # Value
            val_lbl = tk.Label(grid_frame,
                             text="",
                             font=('Segoe UI', 10, 'bold'),
                             bg=self.colors['surface'],
                             fg=self.colors['text'])
            val_lbl.grid(row=row, column=col+2, sticky="w")
            self.metadata_labels[key] = val_lbl
    
    def setup_summary_section(self):
        """Setup the summary text section"""
        summary_frame = tk.Frame(self.container, bg=self.colors['surface'])
        summary_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        tk.Label(summary_frame, 
                text="Summary:", 
                font=('Segoe UI', 10, 'bold'),
                bg=self.colors['surface'],
                fg=self.colors['text']).pack(anchor="w")
        
        summary_container = tk.Frame(summary_frame, bg=self.colors['surface'])
        summary_container.pack(fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(summary_container)
        scrollbar.pack(side="right", fill="y")
        
        self.summary_text = tk.Text(summary_container,
                                   wrap="word",
                                   font=('Segoe UI', 10),
                                   bg=self.colors['surface'],
                                   fg=self.colors['text'],
                                   bd=0,
                                   relief="flat",
                                   yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.summary_text.yview)
        self.summary_text.pack(fill="both", expand=True)
    
    def setup_quality_section(self):
        """Setup the quality list section"""
        quality_frame = tk.Frame(self.container, bg=self.colors['surface'])
        quality_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(quality_frame, 
                text="Available Qualities", 
                font=('Segoe UI', 10, 'bold'),
                bg=self.colors['surface'],
                fg=self.colors['text']).pack(anchor="w")
        
        self.quality_list = QualityList(quality_frame, colors=self.colors)
        self.quality_list.pack(fill="x")
    
    def setup_action_buttons(self):
        """Setup action buttons (bookmark, download)"""
        button_frame = tk.Frame(self.container, bg=self.colors['surface'])
        button_frame.pack(fill="x", pady=(10, 0))
        
        # Bookmark button
        self.bookmark_btn = tk.Button(button_frame,
                                     text="⭐ Bookmark",
                                     bg=self.colors['primary'],
                                     fg='white',
                                     width=12,
                                     state="disabled")
        self.bookmark_btn.pack(side="left", padx=(0, 10))
        
        # Download button
        self.download_btn = tk.Button(button_frame,
                                     text="⬇️ Download",
                                     bg=self.colors['success'],
                                     fg='white',
                                     width=12,
                                     state="disabled")
        self.download_btn.pack(side="left")

    def setup_action_buttons(self):
        """Setup action buttons"""
        button_frame = tk.Frame(self.container, bg=self.colors['surface'])
        button_frame.pack(fill="x", pady=(10, 0))
        
        # Bookmark button
        self.bookmark_btn = tk.Button(button_frame,
                                     text="⭐ Bookmark",
                                     bg=self.colors['primary'],
                                     fg='white',
                                     width=12,
                                     state="disabled")
        self.bookmark_btn.pack(side="left", padx=(0, 10))
        
        # Download button
        self.download_btn = tk.Button(button_frame,
                                     text="⬇️ Download",
                                     bg=self.colors['success'],
                                     fg='white',
                                     width=12,
                                     state="disabled")
        self.download_btn.pack(side="left")
    
    def set_bookmark_state(self, is_bookmarked):
        """Update bookmark button appearance based on state"""
        if is_bookmarked:
            self.bookmark_btn.config(
                text="✅ Bookmarked",
                bg=self.colors['success'],
                fg='white'
            )
        else:
            self.bookmark_btn.config(
                text="⭐ Bookmark",
                bg=self.colors['primary'],
                fg='white'
            )
    
    def add_bookmark_button(self, callback):
        """Connect bookmark button to callback"""
        self.bookmark_callback = callback
        self.bookmark_btn.config(
            command=callback,
            state="normal"
        )
    
    def add_download_button(self, callback):
        """Connect download button to callback"""
        self.download_callback = callback
        self.download_btn.config(
            command=callback,
            state="normal"
        )
    
    def display_movie(self, movie):
        """Display movie details"""
        self.current_movie = movie
        self.clear()
        
        # Update title
        title = movie.get("title", "Unknown")
        self.title_label.config(text=title)
        
        # Update metadata
        if hasattr(self, 'metadata_labels'):
            self.metadata_labels.get("year_label", tk.Label()).config(
                text=str(movie.get("year", ""))
            )
            self.metadata_labels.get("rating_label", tk.Label()).config(
                text=f"{movie.get('rating', 0)}/10"
            )
            self.metadata_labels.get("runtime_label", tk.Label()).config(
                text=f"{movie.get('runtime', 0)} mins"
            )
            
            genres = movie.get("genres", [])
            if isinstance(genres, list):
                self.metadata_labels.get("genre_label", tk.Label()).config(
                    text=", ".join(genres)
                )
        
        # Update summary
        if hasattr(self, 'summary_text'):
            self.summary_text.delete("1.0", "end")
            summary = movie.get("description_full") or movie.get("summary") or "No summary available."
            self.summary_text.insert("end", summary)
        
        # Update quality list
        if hasattr(self, 'quality_list'):
            for torrent in movie.get("torrents", []):
                self.quality_list.add_torrent(torrent)
        
        # Enable buttons
        self.bookmark_btn.config(state="normal")
        self.download_btn.config(state="normal")
        
        # Load poster if available
        poster_url = movie.get("medium_cover_image")
        if poster_url:
            self.load_poster(poster_url)
    
    def load_poster(self, image_url):
        """Load movie poster with proper aspect ratio"""
        def worker():
            try:
                response = requests.get(image_url, timeout=20)
                img = Image.open(BytesIO(response.content))
                
                # Calculate size while maintaining aspect ratio
                max_width = 200   # Increased from 180
                max_height = 300  # Increased from 270
                
                img_ratio = img.width / img.height
                
                if img_ratio > (max_width / max_height):
                    # Image is wider than target ratio
                    new_width = max_width
                    new_height = int(max_width / img_ratio)
                else:
                    # Image is taller than target ratio
                    new_height = max_height
                    new_width = int(max_height * img_ratio)
                
                # High-quality resize
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Create canvas with dark background
                canvas_img = Image.new('RGB', (max_width, max_height), 
                                     color=(26, 31, 46))  # Matches surface color
                
                # Center the image
                x_offset = (max_width - new_width) // 2
                y_offset = (max_height - new_height) // 2
                canvas_img.paste(img, (x_offset, y_offset))
                
                tk_img = ImageTk.PhotoImage(canvas_img)
                self.poster_image_ref = tk_img
                
                # Update UI - CORRECT VERSION
                self.root.after(0, lambda img=tk_img: [
                    self.poster_label.config(
                        image=img, 
                        text="",
                        width=max_width,
                        height=max_height
                    ),
                    setattr(self.poster_label, 'image', img)  # Use setattr inside lambda
                ])
                
            except Exception as e:
                print("Poster load error:", e)
                self.root.after(0, lambda: self.poster_label.config(
                    image="", 
                    text="No Image",
                    width=25,
                    height=12
                ))
        
        threading.Thread(target=worker, daemon=True).start()

    
    def clear(self):
        """Clear all details"""
        if hasattr(self, 'title_label'):
            self.title_label.config(text="Select a movie")
        
        if hasattr(self, 'metadata_labels'):
            for label in self.metadata_labels.values():
                label.config(text="")
        
        if hasattr(self, 'summary_text'):
            self.summary_text.delete("1.0", "end")
        
        if hasattr(self, 'poster_label'):
            self.poster_label.config(image="", text="No Image")
        
        if hasattr(self, 'quality_list'):
            self.quality_list.clear()
        
        # Disable buttons
        if hasattr(self, 'bookmark_btn'):
            self.bookmark_btn.config(state="disabled")
        
        if hasattr(self, 'download_btn'):
            self.download_btn.config(state="disabled")
    
    def get_selected_torrent(self):
        """Get selected torrent from quality list"""
        if hasattr(self, 'quality_list'):
            return self.quality_list.get_selected_torrent()
        return None
    
    def get_movie_title(self):
        """Get current movie title"""
        if self.current_movie:
            return self.current_movie.get("title", "Unknown")
        return "Unknown"