"""
Multi-threaded file indexer with smart diffing and resume capability.
"""

import os
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Set, Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
import multiprocessing

from src.core.database import DatabaseManager
from src.core.logger import get_logger
from src.utils.file_utils import (
    should_index_content,
    safe_read_file,
    get_file_stats,
    is_blacklisted
)


logger = get_logger(__name__)


class FileIndexer:
    """
    High-performance file indexer with multiprocessing support.
    Implements smart diffing to avoid re-indexing unchanged files.
    """
    
    # Textual file extensions that should have content indexed
    TEXT_EXTENSIONS = {
        '.txt', '.md', '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp',
        '.h', '.hpp', '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt',
        '.html', '.css', '.scss', '.sass', '.less', '.xml', '.json', '.yaml', '.yml',
        '.toml', '.ini', '.cfg', '.conf', '.sh', '.bash', '.zsh', '.ps1',
        '.sql', '.r', '.m', '.scala', '.groovy', '.pl', '.lua', '.vim',
        '.log', '.csv', '.tsv', '.rst', '.tex', '.dockerfile'
    }
    
    # Maximum file size to index content (10 MB)
    MAX_CONTENT_SIZE = 10 * 1024 * 1024
    
    def __init__(self, db: DatabaseManager, progress_callback: Callable[[int, int, str], None] = None):
        self.db = db
        self.progress_callback = progress_callback
        self.blacklist = self._load_blacklist()
        self._stop_requested = False
    
    def _load_blacklist(self) -> Set[str]:
        """Load blacklist patterns from database."""
        patterns = self.db.get_blacklist()
        return {pattern for pattern, _ in patterns}
    
    def request_stop(self):
        """Request indexing to stop gracefully."""
        self._stop_requested = True
        logger.info("Stop requested for indexer")
    
    def index_paths(self, root_paths: List[str], full_scan: bool = False):
        """
        Index one or more root paths.
        
        Args:
            root_paths: List of directory or drive paths to index
            full_scan: If True, re-index all files regardless of modification time
        """
        logger.info(f"Starting indexing for {len(root_paths)} path(s), full_scan={full_scan}")
        start_time = time.time()
        
        # Phase A: Discovery - scan all files
        logger.info("Phase A: Discovering files...")
        all_files = []
        existing_paths = set()
        
        for root in root_paths:
            if self._stop_requested:
                logger.info("Indexing stopped during discovery")
                return
            
            discovered = self._discover_files(Path(root))
            all_files.extend(discovered)
            existing_paths.update(str(f['full_path']) for f in discovered)
        
        logger.info(f"Discovered {len(all_files)} files")
        
        # Phase B: Diffing - determine what needs indexing
        logger.info("Phase B: Determining changes...")
        files_to_process = self._diff_files(all_files, full_scan)
        
        if not full_scan:
            # Remove missing files
            self.db.remove_missing_files(existing_paths)
        
        logger.info(f"Need to process {len(files_to_process)} files")
        
        # Phase C: Processing - index in parallel
        if files_to_process:
            logger.info("Phase C: Indexing files...")
            self._process_files(files_to_process)
        
        # Update last scan time
        self.db.set_config('last_full_scan', datetime.now().isoformat())
        
        elapsed = time.time() - start_time
        logger.info(f"Indexing completed in {elapsed:.2f} seconds")
    
    def _discover_files(self, root: Path) -> List[Dict[str, Any]]:
        """
        Recursively discover all files under root path.
        Returns list of file info dictionaries.
        """
        files = []
        
        try:
            for entry in os.scandir(str(root)):
                if self._stop_requested:
                    break
                
                try:
                    # Check blacklist
                    if is_blacklisted(entry.path, self.blacklist):
                        continue
                    
                    if entry.is_file(follow_symlinks=False):
                        stats = get_file_stats(entry.path)
                        if stats:
                            files.append(stats)
                    
                    elif entry.is_dir(follow_symlinks=False):
                        # Recurse into subdirectory
                        files.extend(self._discover_files(Path(entry.path)))
                
                except (PermissionError, OSError) as e:
                    logger.debug(f"Skipping {entry.path}: {e}")
                    continue
        
        except (PermissionError, OSError) as e:
            logger.warning(f"Cannot access {root}: {e}")
        
        return files
    
    def _diff_files(self, discovered_files: List[Dict[str, Any]], full_scan: bool) -> List[Dict[str, Any]]:
        """
        Compare discovered files with database to determine what needs processing.
        """
        files_to_process = []
        
        for file_info in discovered_files:
            
            parent = file_info['parent_path']
            name = file_info['filename']
            
            db_record = self.db.file_exists(parent, name)
            
            if full_scan:
                # Force re-index everything
                files_to_process.append(file_info)
            
            elif db_record is None:
                # New file
                files_to_process.append(file_info)
            
            elif file_info['modified_at'] > db_record['modified_at']:
                # Modified file
                files_to_process.append(file_info)
        
        return files_to_process
    
    def _process_files(self, files: List[Dict[str, Any]]):
        """
        Process files using multiprocessing for speed.
        Batch commits every 500 files.
        """
        total = len(files)
        processed = 0
        batch_size = 500
        
        # Determine worker count (leave 1-2 cores free)
        max_workers = max(1, multiprocessing.cpu_count() - 2)
        
        logger.info(f"Using {max_workers} worker processes")
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit jobs in batches
            batch = []
            futures = {}
            
            for file_info in files:
                if self._stop_requested:
                    logger.info("Stop requested, cancelling remaining jobs")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                
                batch.append(file_info)
                
                if len(batch) >= batch_size:
                    self._submit_batch(executor, batch, futures)
                    batch = []
            
            # Submit remaining files
            if batch and not self._stop_requested:
                self._submit_batch(executor, batch, futures)
            
            # Collect results
            for future in as_completed(futures):
                if self._stop_requested:
                    break
                
                try:
                    result = future.result(timeout=5)
                    if result:
                        file_id, content = result
                        if content is not None:
                            self.db.upsert_content(file_id, content)
                    
                    processed += 1
                    
                    if self.progress_callback:
                        file_info = futures[future]
                        self.progress_callback(
                            processed,
                            total,
                            f"Processing {file_info['filename']}"
                        )
                
                except Exception as e:
                    file_info = futures[future]
                    logger.error(f"Error processing {file_info['full_path']}: {e}")
                    processed += 1
        
        logger.info(f"Processed {processed}/{total} files")
    
    def _submit_batch(self, executor, batch: List[Dict[str, Any]], futures: Dict):
        """Submit a batch of files for processing."""
        # First, batch insert metadata
        self.db.batch_upsert_files(batch)
        # Fetch IDs for each file so content indexing can reference them
        id_map = self.db.get_file_ids(batch)
        for f in batch:
            key = (f['parent_path'], f['filename'])
            if key in id_map:
                f['id'] = id_map[key]
        
        # Then submit content indexing jobs
        for file_info in batch:
            if should_index_content(file_info, self.MAX_CONTENT_SIZE, self.TEXT_EXTENSIONS):
                future = executor.submit(_index_file_worker, file_info)
                futures[future] = file_info


def _index_file_worker(file_info: Dict[str, Any]) -> tuple:
    """
    Worker function that runs in separate process.
    Reads file content and returns (file_id, content).
    Must be a module-level function for pickling.
    """
    try:
        # Small delay to prevent overwhelming the system
        time.sleep(0.001)
        
        content = safe_read_file(file_info['full_path'])
        
        if content:
            # Create a temporary database connection for this worker
            # Note: We return content and let main process handle DB writes
            # to avoid database locking issues
            return (file_info.get('id'), content)
        
        return None
    
    except Exception as e:
        logger.error(f"Worker error for {file_info['full_path']}: {e}")
        return None
