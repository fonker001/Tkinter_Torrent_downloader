import threading
from tkinter import StringVar, Text
from tkinter.ttk import Frame, Scrollbar
from ttkbootstrap.widgets import Entry, Button, Treeview, Label
from PIL import Image, ImageTk
from io import BytesIO
import requests

from src.utils.image_loader import load_image_from_url

class SearchFrame(Frame):
    def __init__(self, parent, search_callback):
        super().__init__(parent)
        self.search_callback = search_callback
        self.search_var = StringVar()
        
        self.search_entry = Entry(self, textvariable=self.search_var, width=50)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.search_entry.bind('<Return>', lambda e: search_callback())
        
        self.search_btn = Button(self, text="Search", command=search_callback)
        self.search_btn.pack(side="left")
    
    def get_search_term(self):
        return self.search_var.get().strip()
    
    def disable_search(self):
        self.search_btn.config(state="disabled")
    
    def enable_search(self):
        self.search_btn.config(state="normal")

class MovieList(Frame):
    def __init__(self, parent, selection_callback):
        super().__init__(parent)
        self.selection_callback = selection_callback
        self.setup_treeview()
    
    def setup_treeview(self):
        Label(self, text="Movies", font=('Helvetica', 10, 'bold')).pack(anchor="w")
        
        tree_scroll = Scrollbar(self)
        tree_scroll.pack(side="right", fill="y")
        
        self.tree = Treeview(
            self, 
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
        self.tree.bind("<<TreeviewSelect>>", self.on_selection)
    
    def on_selection(self, event):
        selected = self.tree.item(self.tree.focus())["values"]
        if selected and len(selected) >= 4:
            self.selection_callback(selected[3])
    
    def add_movie(self, movie):
        self.tree.insert("", "end", values=(
            movie["title"],
            movie["year"],
            f"{movie['rating']}/10",
            movie["id"]
        ))
    
    def clear(self):
        self.tree.delete(*self.tree.get_children())

class MovieDetails(Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.poster_image_ref = None
        self.current_movie = None
        self.setup_ui()
    
    def setup_ui(self):
        # Top section: Poster and basic info
        top_frame = Frame(self)
        top_frame.pack(fill="x", pady=(0, 10))
        
        self.poster_label = Label(top_frame, width=25)
        self.poster_label.pack(side="left", padx=(0, 10))
        
        info_frame = Frame(top_frame)
        info_frame.pack(side="left", fill="both", expand=True)
        
        self.title_label = Label(info_frame, text="", font=("Helvetica", 14, "bold"), wraplength=400)
        self.title_label.pack(anchor="w", pady=(0, 5))
        
        self.meta_frame = Frame(info_frame)
        self.meta_frame.pack(anchor="w")
        
        self.create_metadata_grid()
        
        # Summary section
        summary_frame = Frame(self)
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
        quality_frame = Frame(self)
        quality_frame.pack(fill="x", pady=(0, 10))
        
        Label(quality_frame, text="Available Qualities", font=('Helvetica', 10, 'bold')).pack(anchor="w")
        
        self.quality_list = QualityList(quality_frame)
        self.quality_list.pack(fill="x")
    
    def create_metadata_grid(self):
        self.metadata_labels = {}
        for i, (label, key) in enumerate([
            ("Year:", "year_label"),
            ("Rating:", "rating_label"),
            ("Runtime:", "runtime_label"), 
            ("Genres:", "genre_label")
        ]):
            Label(self.meta_frame, text=label).grid(row=i, column=0, sticky="e", padx=(0, 5))
            label_widget = Label(self.meta_frame, text="")
            label_widget.grid(row=i, column=1, sticky="w")
            self.metadata_labels[key] = label_widget
    
    def display_movie(self, movie):
        self.current_movie = movie
        self.clear()
        
        self.title_label.config(text=movie.get("title", "N/A"))
        self.metadata_labels["year_label"].config(text=str(movie.get("year", "")))
        self.metadata_labels["rating_label"].config(text=f"{movie.get('rating', 0)}/10")
        self.metadata_labels["runtime_label"].config(text=f"{movie.get('runtime', 0)} mins")
        self.metadata_labels["genre_label"].config(text=", ".join(movie.get("genres", ["N/A"])))
        
        self.summary_text.delete(1.0, "end")
        self.summary_text.insert("end", movie.get("description_full", "No summary available."))
        
        for torrent in movie.get("torrents", []):
            self.quality_list.add_torrent(torrent)
    
    def load_poster(self, image_url):
        try:
            image = load_image_from_url(image_url, (180, 270))
            if image:
                self.root.after(0, lambda: [
                    self.poster_label.config(image=image),
                    setattr(self.poster_label, 'image', image),
                    setattr(self, 'poster_image_ref', image)
                ])
        except Exception as e:
            self.root.after(0, lambda: [
                self.poster_label.config(image="", text="No Image Available")
            ])
    
    def get_selected_torrent(self):
        return self.quality_list.get_selected_torrent()
    
    def get_movie_title(self):
        return self.current_movie.get("title", "Unknown") if self.current_movie else "Unknown"
    
    def clear(self):
        self.title_label.config(text="")
        for label in self.metadata_labels.values():
            label.config(text="")
        self.summary_text.delete(1.0, "end")
        self.poster_label.config(image="", text="No Image Selected")
        self.quality_list.clear()

class QualityList(Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setup_treeview()
    
    def setup_treeview(self):
        scroll = Scrollbar(self)
        scroll.pack(side="right", fill="y")
        
        self.tree = Treeview(
            self,
            columns=("Quality", "Size", "Type", "Seeds", "Date", "Torrent"),
            show="headings",
            height=5,
            yscrollcommand=scroll.set
        )
        scroll.config(command=self.tree.yview)
        
        for col, width in [("Quality", 70), ("Size", 80), ("Type", 60), ("Seeds", 60), ("Date", 80)]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor="center")
        self.tree.column("Torrent", width=0, stretch=False)
        
        self.tree.pack(fill="x")
    
    def add_torrent(self, torrent):
        from datetime import datetime
        date_str = datetime.fromtimestamp(torrent["date_uploaded_unix"]).strftime("%Y-%m-%d")
        self.tree.insert("", "end", values=(
            torrent["quality"],
            torrent["size"],
            torrent["type"].capitalize(),
            torrent["seeds"],
            date_str,
            torrent["url"]
        ))
    
    def get_selected_torrent(self):
        selected = self.tree.item(self.tree.focus())["values"]
        if selected and len(selected) >= 6:
            return {
                'quality': selected[0],
                'size': selected[1],
                'type': selected[2],
                'seeds': selected[3],
                'date': selected[4],
                'url': selected[5]
            }
        return None
    
    def clear(self):
        self.tree.delete(*self.tree.get_children())