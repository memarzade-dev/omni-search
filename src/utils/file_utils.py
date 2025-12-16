"""
File handling utilities with safe encoding detection.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, Set
from datetime import datetime

from src.core.logger import get_logger


logger = get_logger(__name__)


def get_file_stats(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Get file statistics safely.
    Returns None if file cannot be accessed.
    """
    try:
        path = Path(filepath)
        stat = os.stat(filepath)
        
        return {
            'full_path': str(path.resolve()),
            'parent_path': str(path.parent),
            'filename': path.name,
            'extension': path.suffix.lower(),
            'size_bytes': stat.st_size,
            'created_at': int(stat.st_ctime),
            'modified_at': int(stat.st_mtime),
            'indexed_at': int(datetime.now().timestamp())
        }
    
    except Exception as e:
        logger.debug(f"Cannot get stats for {filepath}: {e}")
        return None


def safe_read_file(filepath: str, max_size: int = 10 * 1024 * 1024) -> Optional[str]:
    """
    Safely read text file content with encoding detection.
    
    Args:
        filepath: Path to file
        max_size: Maximum file size to read (default 10MB)
    
    Returns:
        File content as string, or None if unreadable
    """
    try:
        # Check size first
        size = os.path.getsize(filepath)
        if size > max_size:
            return None
        
        # Try UTF-8 first (most common)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            pass
        
        # Try with error handling
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    except Exception as e:
        logger.debug(f"Cannot read {filepath}: {e}")
        return None


def should_index_content(
    file_info: Dict[str, Any],
    max_size: int,
    text_extensions: Set[str]
) -> bool:
    """
    Determine if file content should be indexed.
    
    Args:
        file_info: File metadata dictionary
        max_size: Maximum file size to index
        text_extensions: Set of text file extensions
    
    Returns:
        True if content should be indexed
    """
    # Check size
    if file_info.get('size_bytes', 0) > max_size:
        return False
    
    # Check extension
    ext = file_info.get('extension', '').lower()
    return ext in text_extensions


def is_blacklisted(filepath: str, blacklist: Set[str]) -> bool:
    """
    Check if path should be blacklisted.
    
    Args:
        filepath: Path to check
        blacklist: Set of blacklist patterns
    
    Returns:
        True if path should be skipped
    """
    path = Path(filepath)
    
    # Check each part of the path
    for part in path.parts:
        if part in blacklist:
            return True
    
    # Check extension
    if path.suffix in blacklist:
        return True
    
    return False


def format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def format_timestamp(timestamp: int) -> str:
    """Format Unix timestamp to readable date string."""
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return "Unknown"