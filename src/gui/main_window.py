"""
Main GUI window using CustomTkinter.
Modern, responsive interface for Windows 11.
"""

import customtkinter as ctk
from pathlib import Path
from typing import Optional
import threading

from src.core.database import DatabaseManager
from src.core.indexer import FileIndexer
from src.core.searcher import SearchEngine
from src.utils.markdown_generator import MarkdownReportGenerator
from src.gui.indexing_tab import IndexingTab
from src.gui.search_tab import SearchTab
from src.gui.settings_tab import SettingsTab
from src.core.logger import get_logger


logger = get_logger(__name__)

# Application paths
APP_DIR = Path.home() / ".omnisearch"
DB_PATH = APP_DIR / "index.db"
REPORTS_DIR = APP_DIR / "reports"

# Ensure directories exist
APP_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class OmniSearchApp:
    """Main application class."""
    
    def __init__(self):
        logger.info("Initializing OmniSearch Pro")
        
        # Set appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create main window
        self.root = ctk.CTk()
        self.root.title("OmniSearch Pro - Enterprise File Search")
        self.root.geometry("1200x800")
        
        # Initialize core components
        self.db = DatabaseManager(DB_PATH)
        self.indexer = FileIndexer(self.db)
        self.searcher = SearchEngine(self.db)
        self.report_generator = MarkdownReportGenerator()
        
        # Build UI
        self._build_ui()
        
        # Load initial stats
        self._update_stats()
        
        logger.info("Application initialized successfully")
    
    def _build_ui(self):
        """Build the main user interface."""
        # Configure grid
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        
        # Sidebar
        self.sidebar = ctk.CTkFrame(self.root, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar.grid_rowconfigure(4, weight=1)
        
        # Logo/Title
        self.logo_label = ctk.CTkLabel(
            self.sidebar,
            text="OmniSearch Pro",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Stats display
        self.stats_frame = ctk.CTkFrame(self.sidebar)
        self.stats_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        self.stats_label = ctk.CTkLabel(
            self.stats_frame,
            text="Database Stats",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.stats_label.grid(row=0, column=0, padx=10, pady=5)
        
        self.files_label = ctk.CTkLabel(
            self.stats_frame,
            text="Files: 0",
            font=ctk.CTkFont(size=11)
        )
        self.files_label.grid(row=1, column=0, padx=10, pady=2)
        
        self.indexed_label = ctk.CTkLabel(
            self.stats_frame,
            text="Indexed: 0",
            font=ctk.CTkFont(size=11)
        )
        self.indexed_label.grid(row=2, column=0, padx=10, pady=2)
        
        # Tab view
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        # Create tabs
        self.tabview.add("Indexing")
        self.tabview.add("Search")
        self.tabview.add("Settings")
        
        # Initialize tab contents
        self.indexing_tab = IndexingTab(
            self.tabview.tab("Indexing"),
            self.db,
            self.indexer,
            self._update_stats
        )
        
        self.search_tab = SearchTab(
            self.tabview.tab("Search"),
            self.searcher,
            self.report_generator,
            REPORTS_DIR
        )
        
        self.settings_tab = SettingsTab(
            self.tabview.tab("Settings"),
            self.db
        )
    
    def _update_stats(self):
        """Update statistics display."""
        try:
            stats = self.db.get_stats()
            self.files_label.configure(text=f"Files: {stats['total_files']:,}")
            self.indexed_label.configure(text=f"Indexed: {stats['indexed_files']:,}")
        except Exception as e:
            logger.error(f"Error updating stats: {e}")
    
    def run(self):
        """Start the application main loop."""
        logger.info("Starting GUI main loop")
        self.root.mainloop()
        
        # Cleanup on exit
        logger.info("Application closing")
        self.db.close()