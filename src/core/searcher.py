"""
Advanced search engine with regex and content search support.
"""

import re
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.core.database import DatabaseManager
from src.core.logger import get_logger


logger = get_logger(__name__)


class SearchEngine:
    """
    Advanced search engine with multiple filter options.
    Handles both metadata and full-text searches.
    """
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def search(
        self,
        keyword: str = "",
        regex_mode: bool = False,
        case_sensitive: bool = False,
        search_content: bool = True,
        extensions: Optional[List[str]] = None,
        min_size_mb: Optional[float] = None,
        max_size_mb: Optional[float] = None,
        modified_after: Optional[int] = None,
        modified_before: Optional[int] = None,
        paths: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute search with given parameters.
        
        Returns:
            List of matching files with metadata and optional content snippets
        """
        logger.info(f"Searching: keyword='{keyword}', content={search_content}, regex={regex_mode}")
        
        # Build query parameters
        query_params = {
            'keyword': keyword,
            'regex_mode': regex_mode,
            'case_sensitive': case_sensitive,
            'search_content': search_content,
            'extensions': extensions or [],
            'paths': paths or []
        }
        
        # Convert sizes from MB to bytes
        if min_size_mb is not None:
            query_params['min_size'] = int(min_size_mb * 1024 * 1024)
        
        if max_size_mb is not None:
            query_params['max_size'] = int(max_size_mb * 1024 * 1024)
        
        if modified_after is not None:
            query_params['modified_after'] = modified_after
        
        if modified_before is not None:
            query_params['modified_before'] = modified_before
        
        # Execute database search
        results = self.db.search(query_params)
        
        # Post-process for regex if needed
        if regex_mode and keyword:
            results = self._filter_regex(results, keyword, case_sensitive, search_content)
        
        logger.info(f"Found {len(results)} matching files")
        
        return results
    
    def _filter_regex(
        self,
        results: List[Dict[str, Any]],
        pattern: str,
        case_sensitive: bool,
        search_content: bool
    ) -> List[Dict[str, Any]]:
        """
        Apply regex filtering to results.
        SQLite FTS doesn't support regex, so we do it post-query.
        """
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
            return []
        
        filtered = []
        
        for result in results:
            # Check filename
            if regex.search(result['filename']):
                filtered.append(result)
                continue
            
            # Check content snippet if available
            if search_content and result.get('snippet'):
                # Remove HTML tags from snippet
                clean_snippet = re.sub(r'<[^>]+>', '', result['snippet'])
                if regex.search(clean_snippet):
                    filtered.append(result)
        
        return filtered
    
    def get_file_context(self, filepath: str, keyword: str, lines_context: int = 3) -> List[str]:
        """
        Get context around keyword matches in a file.
        Returns list of text snippets with surrounding lines.
        """
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            matches = []
            keyword_lower = keyword.lower()
            
            for i, line in enumerate(lines):
                if keyword_lower in line.lower():
                    # Get context
                    start = max(0, i - lines_context)
                    end = min(len(lines), i + lines_context + 1)
                    
                    context_lines = []
                    for j in range(start, end):
                        prefix = ">>> " if j == i else "    "
                        context_lines.append(f"{prefix}{lines[j].rstrip()}")
                    
                    matches.append("\n".join(context_lines))
            
            return matches
        
        except Exception as e:
            logger.error(f"Error reading file context {filepath}: {e}")
            return []