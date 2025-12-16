"""
Indexing tab for scanning and updating the file database.
"""

import customtkinter as ctk
from pathlib import Path
import threading
from tkinter import filedialog
from typing import Callable

from src.core.database import DatabaseManager
from src.core.indexer import FileIndexer
from src.core.logger import get_logger


logger = get_logger(__name__)


class IndexingTab:
    """Tab for managing file indexing operations."""
    
    def __init__(
        self,
        parent: ctk.CTkFrame,
        db: DatabaseManager,
        indexer: FileIndexer,
        stats_callback: Callable
    ):
        self.parent = parent
        self.db = db
        self.indexer = indexer
        self.stats_callback = stats_callback
        
        self.is_indexing = False
        self.indexing_thread: threading.Thread = None
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the indexing tab interface."""
        # Configure grid
        self.parent.grid_columnconfigure(0, weight=1)
        
        # Title
        title = ctk.CTkLabel(
            self.parent,
            text="File Indexing",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Path selection frame
        path_frame = ctk.CTkFrame(self.parent)
        path_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        path_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            path_frame,
            text="Paths to Index:",
            font=ctk.CTkFont(size=12)
        ).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        self.path_entry = ctk.CTkEntry(
            path_frame,
            placeholder_text="C:\\ or select folder..."
        )
        self.path_entry.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        browse_btn = ctk.CTkButton(
            path_frame,
            text="Browse",
            width=100,
            command=self._browse_folder
        )
        browse_btn.grid(row=1, column=1, padx=10, pady=5)
        
        # Options frame
        options_frame = ctk.CTkFrame(self.parent)
        options_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        self.full_scan_var = ctk.BooleanVar(value=False)
        self.full_scan_check = ctk.CTkCheckBox(
            options_frame,
            text="Full Scan (re-index all files, slower)",
            variable=self.full_scan_var
        )
        self.full_scan_check.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # Action buttons
        button_frame = ctk.CTkFrame(self.parent)
        button_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        self.start_btn = ctk.CTkButton(
            button_frame,
            text="Start Indexing",
            command=self._start_indexing,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.start_btn.grid(row=0, column=0, padx=10, pady=10)
        
        self.stop_btn = ctk.CTkButton(
            button_frame,
            text="Stop",
            command=self._stop_indexing,
            fg_color="red",
            hover_color="darkred",
            state="disabled"
        )
        self.stop_btn.grid(row=0, column=1, padx=10, pady=10)
        
        # Progress frame
        progress_frame = ctk.CTkFrame(self.parent)
        progress_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)
        
        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text="Ready to index",
            font=ctk.CTkFont(size=11)
        )
        self.progress_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="ew")
        self.progress_bar.set(0)
        
        # Log text area
        log_frame = ctk.CTkFrame(self.parent)
        log_frame.grid(row=5, column=0, padx=20, pady=10, sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        self.parent.grid_rowconfigure(5, weight=1)
        
        self.log_text = ctk.CTkTextbox(log_frame, height=200)
        self.log_text.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.log_text.configure(state="disabled")
    
    def _browse_folder(self):
        """Open folder browser dialog."""
        folder = filedialog.askdirectory(title="Select Folder to Index")
        if folder:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)
    
    def _start_indexing(self):
        """Start the indexing process in a background thread."""
        if self.is_indexing:
            return
        
        path_text = self.path_entry.get().strip()
        if not path_text:
            self._log("Error: Please specify a path to index")
            return
        
        paths = [p.strip() for p in path_text.split(";") if p.strip()]
        
        # Validate paths
        valid_paths = []
        for p in paths:
            if Path(p).exists():
                valid_paths.append(p)
            else:
                self._log(f"Warning: Path does not exist: {p}")
        
        if not valid_paths:
            self._log("Error: No valid paths to index")
            return
        
        self.is_indexing = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_bar.set(0)
        self._log(f"Starting indexing for {len(valid_paths)} path(s)...")
        
        # Start indexing in background thread
        self.indexing_thread = threading.Thread(
            target=self._index_worker,
            args=(valid_paths, self.full_scan_var.get()),
            daemon=True
        )
        self.indexing_thread.start()
    
    def _stop_indexing(self):
        """Request indexing to stop."""
        if self.is_indexing:
            self._log("Stopping indexing...")
            self.indexer.request_stop()
            self.stop_btn.configure(state="disabled")
    
    def _index_worker(self, paths: list, full_scan: bool):
        """Worker thread for indexing."""
        try:
            def progress_callback(current, total, message):
                """Update progress from indexer."""
                if total > 0:
                    progress = current / total
                    self.parent.after(0, lambda: self.progress_bar.set(progress))
                
                self.parent.after(0, lambda: self.progress_label.configure(
                    text=f"Processing {current}/{total}: {message}"
                ))
            
            # Create new indexer instance with callback
            self.indexer.progress_callback = progress_callback
            
            # Run indexing
            self.indexer.index_paths(paths, full_scan)
            
            self.parent.after(0, lambda: self._log("Indexing completed successfully"))
            self.parent.after(0, lambda: self.progress_bar.set(1.0))
            
        except Exception as e:
            logger.error(f"Indexing error: {e}", exc_info=True)
            self.parent.after(0, lambda: self._log(f"Error: {e}"))
        
        finally:
            self.parent.after(0, self._indexing_finished)
    
    def _indexing_finished(self):
        """Called when indexing completes or stops."""
        self.is_indexing = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.stats_callback()
    
    def _log(self, message: str):
        """Add message to log text area."""
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")