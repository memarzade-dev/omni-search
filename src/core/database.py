"""
Thread-safe database manager with FTS5 support.
Handles all SQLite operations with proper connection pooling.
"""

import sqlite3
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from datetime import datetime

from src.core.logger import get_logger


logger = get_logger(__name__)


class DatabaseManager:
    """
    Thread-safe SQLite database manager with FTS5 full-text search.
    Implements connection pooling and proper transaction management.
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.local = threading.local()
        self._lock = threading.Lock()
        self._init_database()
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self.local, 'conn') or self.local.conn is None:
            self.local.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0
            )
            self.local.conn.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self.local.conn.execute("PRAGMA journal_mode=WAL")
            self.local.conn.execute("PRAGMA synchronous=NORMAL")
            self.local.conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        return self.local.conn
    
    @contextmanager
    def get_cursor(self):
        """Context manager for safe cursor operations."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}", exc_info=True)
            raise
        finally:
            cursor.close()
    
    def _init_database(self):
        """Initialize database schema if not exists."""
        logger.info(f"Initializing database at {self.db_path}")
        
        with self.get_cursor() as cursor:
            # Config table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # Blacklist table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blacklist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern TEXT NOT NULL UNIQUE,
                    type TEXT DEFAULT 'folder'
                )
            """)
            
            # Files metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_path TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    extension TEXT,
                    size_bytes INTEGER,
                    created_at INTEGER,
                    modified_at INTEGER,
                    indexed_at INTEGER,
                    checksum TEXT,
                    UNIQUE(parent_path, filename)
                )
            """)
            
            # Indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_path ON files(parent_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ext ON files(extension)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mod ON files(modified_at)")
            
            # FTS5 virtual table for content search
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS file_contents USING fts5(
                    file_id UNINDEXED,
                    content_text,
                    tokenize='trigram'
                )
            """)
            
            # Initialize default blacklist
            self._init_default_blacklist(cursor)
            
            # Set initial config
            cursor.execute(
                "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
                ("version", "1.0.0")
            )
            cursor.execute(
                "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
                ("last_full_scan", "")
            )
            
        logger.info("Database initialized successfully")
    
    def _init_default_blacklist(self, cursor):
        """Initialize default blacklist patterns."""
        default_patterns = [
            ("$RECYCLE.BIN", "folder"),
            ("System Volume Information", "folder"),
            (".git", "folder"),
            (".svn", "folder"),
            ("__pycache__", "folder"),
            ("node_modules", "folder"),
            (".idea", "folder"),
            (".vscode", "folder"),
            ("Windows", "folder"),
            ("Program Files", "folder"),
            ("Program Files (x86)", "folder"),
            (".tmp", "extension"),
            (".temp", "extension"),
            (".cache", "extension"),
        ]
        
        for pattern, pattern_type in default_patterns:
            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO blacklist (pattern, type) VALUES (?, ?)",
                    (pattern, pattern_type)
                )
            except sqlite3.IntegrityError:
                pass  # Pattern already exists
    
    def get_config(self, key: str) -> Optional[str]:
        """Get configuration value."""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else None
    
    def set_config(self, key: str, value: str):
        """Set configuration value."""
        with self.get_cursor() as cursor:
            cursor.execute(
                "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                (key, value)
            )
    
    def get_blacklist(self) -> List[Tuple[str, str]]:
        """Get all blacklist patterns."""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT pattern, type FROM blacklist")
            return [(row['pattern'], row['type']) for row in cursor.fetchall()]
    
    def add_blacklist(self, pattern: str, pattern_type: str = "folder"):
        """Add pattern to blacklist."""
        with self.get_cursor() as cursor:
            cursor.execute(
                "INSERT OR IGNORE INTO blacklist (pattern, type) VALUES (?, ?)",
                (pattern, pattern_type)
            )
    
    def remove_blacklist(self, pattern: str):
        """Remove pattern from blacklist."""
        with self.get_cursor() as cursor:
            cursor.execute("DELETE FROM blacklist WHERE pattern = ?", (pattern,))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM files")
            total = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(DISTINCT extension) as ext_count FROM files")
            ext_count = cursor.fetchone()['ext_count']
            
            cursor.execute("SELECT SUM(size_bytes) as total_size FROM files")
            total_size = cursor.fetchone()['total_size'] or 0
            
            cursor.execute("SELECT COUNT(*) as indexed FROM file_contents")
            indexed = cursor.fetchone()['indexed']
            
            return {
                'total_files': total,
                'total_size': total_size,
                'unique_extensions': ext_count,
                'indexed_files': indexed
            }
    
    def file_exists(self, parent_path: str, filename: str) -> Optional[int]:
        """Check if file exists in database, return its ID."""
        with self.get_cursor() as cursor:
            cursor.execute(
                "SELECT id, modified_at FROM files WHERE parent_path = ? AND filename = ?",
                (parent_path, filename)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def upsert_file(self, file_info: Dict[str, Any]) -> int:
        """Insert or update file metadata. Returns file ID."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO files (parent_path, filename, extension, size_bytes, 
                                   created_at, modified_at, indexed_at, checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(parent_path, filename) DO UPDATE SET
                    extension=excluded.extension,
                    size_bytes=excluded.size_bytes,
                    modified_at=excluded.modified_at,
                    indexed_at=excluded.indexed_at,
                    checksum=excluded.checksum
            """, (
                file_info['parent_path'],
                file_info['filename'],
                file_info.get('extension'),
                file_info.get('size_bytes'),
                file_info.get('created_at'),
                file_info.get('modified_at'),
                file_info.get('indexed_at'),
                file_info.get('checksum')
            ))
            
            # Get the file ID
            cursor.execute(
                "SELECT id FROM files WHERE parent_path = ? AND filename = ?",
                (file_info['parent_path'], file_info['filename'])
            )
            return cursor.fetchone()['id']
    
    def upsert_content(self, file_id: int, content: str):
        """Insert or update file content in FTS5 table."""
        with self.get_cursor() as cursor:
            # Delete old content first
            cursor.execute("DELETE FROM file_contents WHERE file_id = ?", (file_id,))
            # Insert new content
            cursor.execute(
                "INSERT INTO file_contents (file_id, content_text) VALUES (?, ?)",
                (file_id, content)
            )
    
    def batch_upsert_files(self, files_info: List[Dict[str, Any]]):
        """Batch insert/update files for better performance."""
        if not files_info:
            return
        
        with self.get_cursor() as cursor:
            cursor.executemany("""
                INSERT INTO files (parent_path, filename, extension, size_bytes, 
                                   created_at, modified_at, indexed_at, checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(parent_path, filename) DO UPDATE SET
                    extension=excluded.extension,
                    size_bytes=excluded.size_bytes,
                    modified_at=excluded.modified_at,
                    indexed_at=excluded.indexed_at,
                    checksum=excluded.checksum
            """, [
                (
                    f['parent_path'], f['filename'], f.get('extension'),
                    f.get('size_bytes'), f.get('created_at'), f.get('modified_at'),
                    f.get('indexed_at'), f.get('checksum')
                ) for f in files_info
            ])

    def get_file_ids(self, files_info: List[Dict[str, Any]]) -> Dict[tuple, int]:
        """Return IDs for given (parent_path, filename) pairs."""
        ids: Dict[tuple, int] = {}
        if not files_info:
            return ids
        with self.get_cursor() as cursor:
            for f in files_info:
                cursor.execute(
                    "SELECT id FROM files WHERE parent_path = ? AND filename = ?",
                    (f['parent_path'], f['filename'])
                )
                row = cursor.fetchone()
                if row:
                    ids[(f['parent_path'], f['filename'])] = row['id']
        return ids
    
    def remove_missing_files(self, existing_files: set):
        """Remove files from database that no longer exist on disk."""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT id, parent_path, filename FROM files")
            all_files = cursor.fetchall()
            
            to_delete = []
            for row in all_files:
                full_path = str(Path(row['parent_path']) / row['filename'])
                if full_path not in existing_files:
                    to_delete.append(row['id'])
            
            if to_delete:
                logger.info(f"Removing {len(to_delete)} missing files from database")
                cursor.executemany("DELETE FROM files WHERE id = ?", [(fid,) for fid in to_delete])
                cursor.executemany("DELETE FROM file_contents WHERE file_id = ?", [(fid,) for fid in to_delete])
    
    def search(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Advanced search with multiple filters.
        
        Args:
            query_params: {
                'keyword': str,
                'regex_mode': bool,
                'case_sensitive': bool,
                'search_content': bool,
                'extensions': List[str],
                'min_size': int,
                'max_size': int,
                'modified_after': int (timestamp),
                'modified_before': int (timestamp),
                'paths': List[str]
            }
        """
        with self.get_cursor() as cursor:
            keyword = query_params.get('keyword', '').strip()
            search_content = query_params.get('search_content', False)
            
            if search_content and keyword:
                # Full-text search
                results = self._fts_search(cursor, query_params)
            else:
                # Metadata-only search (faster)
                results = self._metadata_search(cursor, query_params)
            
            return results
    
    def _fts_search(self, cursor, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Full-text search using FTS5."""
        keyword = params.get('keyword', '').strip()
        
        # Build FTS query
        if params.get('regex_mode'):
            # FTS doesn't support regex directly, fallback to LIKE for now
            # In production, we'd use a hybrid approach
            fts_query = f'"{keyword}"'
        else:
            fts_query = f'"{keyword}"' if ' ' in keyword else keyword + '*'
        
        # Base query
        sql = """
            SELECT 
                f.id, f.parent_path, f.filename, f.extension, 
                f.size_bytes, f.modified_at,
                snippet(file_contents, 1, '<mark>', '</mark>', '...', 32) as snippet
            FROM file_contents fc
            JOIN files f ON fc.file_id = f.id
            WHERE file_contents MATCH ?
        """
        
        sql_params = [fts_query]
        
        # Add filters
        sql, sql_params = self._add_filters(sql, sql_params, params)
        
        sql += " ORDER BY rank LIMIT 1000"
        
        try:
            cursor.execute(sql, sql_params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError as e:
            logger.error(f"FTS search error: {e}")
            return []
    
    def _metadata_search(self, cursor, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search by metadata only (filename, extension, size, date)."""
        keyword = params.get('keyword', '').strip()
        
        sql = """
            SELECT 
                id, parent_path, filename, extension,
                size_bytes, modified_at
            FROM files
            WHERE 1=1
        """
        sql_params = []
        
        # Filename search
        if keyword:
            if params.get('case_sensitive'):
                sql += " AND filename LIKE ?"
                sql_params.append(f"%{keyword}%")
            else:
                sql += " AND filename LIKE ? COLLATE NOCASE"
                sql_params.append(f"%{keyword}%")
        
        # Add other filters
        sql, sql_params = self._add_filters(sql, sql_params, params)
        
        sql += " ORDER BY modified_at DESC LIMIT 1000"
        
        cursor.execute(sql, sql_params)
        return [dict(row) for row in cursor.fetchall()]
    
    def _add_filters(self, sql: str, params: List, filters: Dict[str, Any]) -> Tuple[str, List]:
        """Add common filters to SQL query."""
        # Extension filter
        if filters.get('extensions'):
            ext_list = [e.strip('.').lower() for e in filters['extensions']]
            placeholders = ','.join(['?'] * len(ext_list))
            sql += f" AND LOWER(extension) IN ({placeholders})"
            params.extend(ext_list)
        
        # Size filter
        if filters.get('min_size'):
            sql += " AND size_bytes >= ?"
            params.append(filters['min_size'])
        
        if filters.get('max_size'):
            sql += " AND size_bytes <= ?"
            params.append(filters['max_size'])
        
        # Date filter
        if filters.get('modified_after'):
            sql += " AND modified_at >= ?"
            params.append(filters['modified_after'])
        
        if filters.get('modified_before'):
            sql += " AND modified_at <= ?"
            params.append(filters['modified_before'])
        
        # Path filter
        if filters.get('paths'):
            path_conditions = ' OR '.join(['parent_path LIKE ?'] * len(filters['paths']))
            sql += f" AND ({path_conditions})"
            params.extend([f"{p}%" for p in filters['paths']])
        
        return sql, params
    
    def close(self):
        """Close all database connections."""
        if hasattr(self.local, 'conn') and self.local.conn:
            self.local.conn.close()
            self.local.conn = None
