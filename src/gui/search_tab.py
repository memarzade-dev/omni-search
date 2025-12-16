"""
Search tab for querying the indexed files.
"""

import customtkinter as ctk
from pathlib import Path
from datetime import datetime, timedelta
import threading
from typing import List, Dict, Any

from src.core.searcher import SearchEngine
from src.utils.markdown_generator import MarkdownReportGenerator
from src.core.logger import get_logger


logger = get_logger(__name__)


class SearchTab:
    """Tab for searching indexed files."""
    
    def __init__(
        self,
        parent: ctk.CTkFrame,
        searcher: SearchEngine,
        report_generator: MarkdownReportGenerator,
        reports_dir: Path
    ):
        self.parent = parent
        self.searcher = searcher
        self.report_generator = report_generator
        self.reports_dir = reports_dir
        
        self.current_results: List[Dict[str, Any]] = []
        self.is_searching = False
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the search tab interface."""
        # Configure grid
        self.parent.grid_columnconfigure(0, weight=1)
        self.parent.grid_rowconfigure(4, weight=1)
        
        # Title
        title = ctk.CTkLabel(
            self.parent,
            text="Advanced Search",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Search input frame
        search_frame = ctk.CTkFrame(self.parent)
        search_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)
        
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Enter search query or regex pattern...",
            height=40,
            font=ctk.CTkFont(size=13)
        )
        self.search_entry.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.search_entry.bind("<Return>", lambda e: self._execute_search())
        
        self.search_btn = ctk.CTkButton(
            search_frame,
            text="Search",
            width=120,
            height=40,
            command=self._execute_search
        )
        self.search_btn.grid(row=0, column=1, padx=10, pady=10)
        
        # Options frame
        options_frame = ctk.CTkFrame(self.parent)
        options_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        options_frame.grid_columnconfigure(1, weight=1)
        
        # Checkboxes
        self.regex_var = ctk.BooleanVar(value=False)
        self.case_var = ctk.BooleanVar(value=False)
        self.content_var = ctk.BooleanVar(value=True)
        
        ctk.CTkCheckBox(
            options_frame,
            text="Regex Mode",
            variable=self.regex_var
        ).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        ctk.CTkCheckBox(
            options_frame,
            text="Case Sensitive",
            variable=self.case_var
        ).grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        ctk.CTkCheckBox(
            options_frame,
            text="Search Content",
            variable=self.content_var
        ).grid(row=0, column=2, padx=10, pady=5, sticky="w")
        
        # Advanced filters (collapsible)
        self.filters_frame = ctk.CTkFrame(self.parent)
        self.filters_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.filters_frame.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkLabel(
            self.filters_frame,
            text="Filters:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w")
        
        # Extensions filter
        ctk.CTkLabel(
            self.filters_frame,
            text="Extensions (comma-separated):"
        ).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.ext_entry = ctk.CTkEntry(
            self.filters_frame,
            placeholder_text="e.g., py, js, md"
        )
        self.ext_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        # Size filters
        ctk.CTkLabel(
            self.filters_frame,
            text="Size (MB):"
        ).grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        size_frame = ctk.CTkFrame(self.filters_frame)
        size_frame.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        size_frame.grid_columnconfigure((0, 2), weight=1)
        
        self.min_size_entry = ctk.CTkEntry(size_frame, placeholder_text="Min", width=80)
        self.min_size_entry.grid(row=0, column=0, padx=5)
        
        ctk.CTkLabel(size_frame, text="to").grid(row=0, column=1, padx=5)
        
        self.max_size_entry = ctk.CTkEntry(size_frame, placeholder_text="Max", width=80)
        self.max_size_entry.grid(row=0, column=2, padx=5)
        
        # Date filter
        ctk.CTkLabel(
            self.filters_frame,
            text="Modified in last N days:"
        ).grid(row=3, column=0, padx=10, pady=5, sticky="w")
        
        self.days_entry = ctk.CTkEntry(
            self.filters_frame,
            placeholder_text="e.g., 7",
            width=100
        )
        self.days_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")
        
        # Results area
        results_frame = ctk.CTkFrame(self.parent)
        results_frame.grid(row=4, column=0, padx=20, pady=10, sticky="nsew")
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_rowconfigure(1, weight=1)
        
        # Results header
        results_header = ctk.CTkFrame(results_frame)
        results_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        results_header.grid_columnconfigure(0, weight=1)
        
        self.results_label = ctk.CTkLabel(
            results_header,
            text="Results: 0 files",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.results_label.grid(row=0, column=0, padx=10, sticky="w")
        
        self.export_btn = ctk.CTkButton(
            results_header,
            text="Export to Markdown",
            width=150,
            command=self._export_results,
            state="disabled"
        )
        self.export_btn.grid(row=0, column=1, padx=10)
        
        # Results scrollable frame
        self.results_scroll = ctk.CTkScrollableFrame(results_frame)
        self.results_scroll.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        self.results_scroll.grid_columnconfigure(0, weight=1)
    
    def _execute_search(self):
        """Execute search in background thread."""
        if self.is_searching:
            return
        
        query = self.search_entry.get().strip()
        if not query:
            logger.info("Empty search query")
            return
        
        self.is_searching = True
        self.search_btn.configure(state="disabled", text="Searching...")
        self._clear_results()
        
        # Start search thread
        thread = threading.Thread(
            target=self._search_worker,
            args=(query,),
            daemon=True
        )
        thread.start()
    
    def _search_worker(self, query: str):
        """Worker thread for search operation."""
        try:
            # Parse filters
            extensions = None
            ext_text = self.ext_entry.get().strip()
            if ext_text:
                extensions = [e.strip() for e in ext_text.split(",")]
            
            min_size = None
            max_size = None
            try:
                min_text = self.min_size_entry.get().strip()
                if min_text:
                    min_size = float(min_text)
            except ValueError:
                pass
            
            try:
                max_text = self.max_size_entry.get().strip()
                if max_text:
                    max_size = float(max_text)
            except ValueError:
                pass
            
            modified_after = None
            try:
                days_text = self.days_entry.get().strip()
                if days_text:
                    days = int(days_text)
                    cutoff = datetime.now() - timedelta(days=days)
                    modified_after = int(cutoff.timestamp())
            except ValueError:
                pass
            
            # Execute search
            results = self.searcher.search(
                keyword=query,
                regex_mode=self.regex_var.get(),
                case_sensitive=self.case_var.get(),
                search_content=self.content_var.get(),
                extensions=extensions,
                min_size_mb=min_size,
                max_size_mb=max_size,
                modified_after=modified_after
            )
            
            self.current_results = results
            
            # Update UI in main thread
            self.parent.after(0, lambda: self._display_results(results))
        
        except Exception as e:
            logger.error(f"Search error: {e}", exc_info=True)
            self.parent.after(0, lambda: self._display_error(str(e)))
        
        finally:
            self.parent.after(0, self._search_finished)
    
    def _display_results(self, results: List[Dict[str, Any]]):
        """Display search results in UI."""
        self._clear_results()
        
        count = len(results)
        self.results_label.configure(text=f"Results: {count} files")
        
        if count == 0:
            no_results = ctk.CTkLabel(
                self.results_scroll,
                text="No files found matching the criteria",
                text_color="gray"
            )
            no_results.grid(row=0, column=0, padx=20, pady=20)
        else:
            self.export_btn.configure(state="normal")
            
            for idx, result in enumerate(results[:100]):  # Limit display to 100
                self._create_result_card(idx, result)
            
            if count > 100:
                more_label = ctk.CTkLabel(
                    self.results_scroll,
                    text=f"... and {count - 100} more results (use Markdown export to see all)",
                    text_color="gray"
                )
                more_label.grid(row=100, column=0, padx=20, pady=20)
    
    def _create_result_card(self, index: int, result: Dict[str, Any]):
        """Create a result card widget."""
        card = ctk.CTkFrame(self.results_scroll)
        card.grid(row=index, column=0, padx=5, pady=5, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        
        # Filename
        filename = ctk.CTkLabel(
            card,
            text=result['filename'],
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        filename.grid(row=0, column=0, padx=10, pady=(10, 2), sticky="w")
        
        # Path
        full_path = str(Path(result['parent_path']) / result['filename'])
        path_label = ctk.CTkLabel(
            card,
            text=full_path,
            font=ctk.CTkFont(size=10),
            text_color="gray",
            anchor="w"
        )
        path_label.grid(row=1, column=0, padx=10, pady=2, sticky="w")
        
        # Metadata
        size = self._format_size(result.get('size_bytes', 0))
        modified = self._format_date(result.get('modified_at', 0))
        meta = f"Size: {size} | Modified: {modified}"
        
        meta_label = ctk.CTkLabel(
            card,
            text=meta,
            font=ctk.CTkFont(size=10),
            text_color="lightgray",
            anchor="w"
        )
        meta_label.grid(row=2, column=0, padx=10, pady=(2, 10), sticky="w")
        
        # Open button
        open_btn = ctk.CTkButton(
            card,
            text="Open",
            width=80,
            height=28,
            command=lambda: self._open_file(full_path)
        )
        open_btn.grid(row=0, column=1, rowspan=3, padx=10, pady=10)
    
    def _open_file(self, filepath: str):
        """Open file with default application."""
        import os
        import subprocess
        
        try:
            if os.name == 'nt':  # Windows
                os.startfile(filepath)
            elif os.name == 'posix':  # Linux/Mac
                subprocess.call(['xdg-open', filepath])
        except Exception as e:
            logger.error(f"Error opening file {filepath}: {e}")
    
    def _export_results(self):
        """Export current results to Markdown."""
        if not self.current_results:
            return
        
        query = self.search_entry.get().strip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"search_{timestamp}.md"
        output_path = self.reports_dir / filename
        
        if self.report_generator.generate(self.current_results, query, output_path):
            logger.info(f"Report exported to {output_path}")
            
            # Show success message
            dialog = ctk.CTkInputDialog(
                text=f"Report exported successfully!\n\n{output_path}\n\nOpen folder?",
                title="Export Complete"
            )
            
            # Open folder
            import os
            os.startfile(str(self.reports_dir))
    
    def _clear_results(self):
        """Clear results display."""
        for widget in self.results_scroll.winfo_children():
            widget.destroy()
    
    def _display_error(self, error_msg: str):
        """Display error message."""
        self._clear_results()
        error_label = ctk.CTkLabel(
            self.results_scroll,
            text=f"Error: {error_msg}",
            text_color="red"
        )
        error_label.grid(row=0, column=0, padx=20, pady=20)
    
    def _search_finished(self):
        """Called when search completes."""
        self.is_searching = False
        self.search_btn.configure(state="normal", text="Search")
    
    def _format_size(self, size_bytes: int) -> str:
        """Format byte size to human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def _format_date(self, timestamp: int) -> str:
        """Format timestamp to readable date."""
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d")
        except:
            return "Unknown"