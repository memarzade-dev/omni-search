"""
Settings tab for managing blacklist and configuration.
"""

import customtkinter as ctk

from src.core.database import DatabaseManager
from src.core.logger import get_logger


logger = get_logger(__name__)


class SettingsTab:
    """Tab for application settings."""
    
    def __init__(self, parent: ctk.CTkFrame, db: DatabaseManager):
        self.parent = parent
        self.db = db
        
        self._build_ui()
        self._load_blacklist()
    
    def _build_ui(self):
        """Build the settings tab interface."""
        # Configure grid
        self.parent.grid_columnconfigure(0, weight=1)
        self.parent.grid_rowconfigure(2, weight=1)
        
        # Title
        title = ctk.CTkLabel(
            self.parent,
            text="Settings",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Blacklist section
        blacklist_frame = ctk.CTkFrame(self.parent)
        blacklist_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        blacklist_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            blacklist_frame,
            text="Blacklist (paths/patterns to exclude from indexing):",
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        # Add pattern controls
        add_frame = ctk.CTkFrame(blacklist_frame)
        add_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        add_frame.grid_columnconfigure(0, weight=1)
        
        self.pattern_entry = ctk.CTkEntry(
            add_frame,
            placeholder_text="Enter folder name or extension (e.g., .tmp)"
        )
        self.pattern_entry.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        add_btn = ctk.CTkButton(
            add_frame,
            text="Add",
            width=80,
            command=self._add_pattern
        )
        add_btn.grid(row=0, column=1, padx=5, pady=5)
        
        # Blacklist display
        list_frame = ctk.CTkFrame(self.parent)
        list_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        
        self.blacklist_scroll = ctk.CTkScrollableFrame(list_frame)
        self.blacklist_scroll.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.blacklist_scroll.grid_columnconfigure(0, weight=1)
        
        # Info section
        info_frame = ctk.CTkFrame(self.parent)
        info_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        info_text = (
            "Note: Changes to blacklist take effect on next indexing operation.\n"
            "Default patterns (like Windows, Program Files) protect system stability."
        )
        
        info_label = ctk.CTkLabel(
            info_frame,
            text=info_text,
            font=ctk.CTkFont(size=10),
            text_color="gray",
            justify="left"
        )
        info_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
    
    def _load_blacklist(self):
        """Load and display blacklist patterns."""
        # Clear existing items
        for widget in self.blacklist_scroll.winfo_children():
            widget.destroy()
        
        # Get patterns from database
        patterns = self.db.get_blacklist()
        
        if not patterns:
            no_items = ctk.CTkLabel(
                self.blacklist_scroll,
                text="No blacklist patterns",
                text_color="gray"
            )
            no_items.grid(row=0, column=0, padx=10, pady=10)
            return
        
        # Display each pattern
        for idx, (pattern, pattern_type) in enumerate(patterns):
            self._create_pattern_item(idx, pattern, pattern_type)
    
    def _create_pattern_item(self, index: int, pattern: str, pattern_type: str):
        """Create a blacklist item widget."""
        item_frame = ctk.CTkFrame(self.blacklist_scroll)
        item_frame.grid(row=index, column=0, padx=5, pady=2, sticky="ew")
        item_frame.grid_columnconfigure(0, weight=1)
        
        # Pattern text
        pattern_label = ctk.CTkLabel(
            item_frame,
            text=f"{pattern} ({pattern_type})",
            anchor="w"
        )
        pattern_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Remove button
        remove_btn = ctk.CTkButton(
            item_frame,
            text="Remove",
            width=80,
            height=28,
            fg_color="red",
            hover_color="darkred",
            command=lambda p=pattern: self._remove_pattern(p)
        )
        remove_btn.grid(row=0, column=1, padx=10, pady=5)
    
    def _add_pattern(self):
        """Add a new blacklist pattern."""
        pattern = self.pattern_entry.get().strip()
        if not pattern:
            return
        
        # Determine type
        pattern_type = "extension" if pattern.startswith(".") else "folder"
        
        try:
            self.db.add_blacklist(pattern, pattern_type)
            self.pattern_entry.delete(0, "end")
            self._load_blacklist()
            logger.info(f"Added blacklist pattern: {pattern}")
        except Exception as e:
            logger.error(f"Error adding pattern: {e}")
    
    def _remove_pattern(self, pattern: str):
        """Remove a blacklist pattern."""
        try:
            self.db.remove_blacklist(pattern)
            self._load_blacklist()
            logger.info(f"Removed blacklist pattern: {pattern}")
        except Exception as e:
            logger.error(f"Error removing pattern: {e}")