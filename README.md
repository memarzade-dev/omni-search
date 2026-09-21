# OmniSearch Pro - Enterprise File Search Engine

A high-performance, local file indexing and search system for Windows 11 that provides instant search across your entire hard drive with advanced filtering capabilities.

## Features

### Core Capabilities
- **Smart Indexing**: Multi-threaded file crawler with resume capability
- **Full-Text Search**: SQLite FTS5-powered content search across millions of files
- **Advanced Filtering**: Search by name, content, extension, size, date, and regex patterns
- **Markdown Reports**: Professional, clickable reports with file links
- **Modern GUI**: Clean, dark-mode interface built with CustomTkinter
- **Safe Operation**: Intelligent resource management prevents system slowdown

### Technical Highlights
- Processes 100,000+ files efficiently using multiprocessing
- Smart diffing avoids re-indexing unchanged files
- Blacklist system protects system folders
- Thread-safe database operations with connection pooling
- Graceful error handling for locked or inaccessible files

## Installation

### Option 1: Run from Source

1. **Requirements**:
   - Python 3.11 or higher
   - Windows 11 (or Windows 10 with compatibility)

2. **Install**:
   ```bash
   git clone https://github.com/oxychain-dev/omnisearch-pro.git
   cd omnisearch-pro
   pip install -r requirements.txt
   ```

3. **Run**:
   ```bash
   python -m src.main
   ```

### Option 2: Standalone Executable

1. **Build**:
   ```bash
   pip install pyinstaller
   python build.py
   ```

2. **Run**: Double-click `dist/OmniSearch Pro.exe`

## Usage

### Quick Start

1. **Indexing** (First Time):
   - Go to "Indexing" tab
   - Enter path (e.g., `C:\` for entire drive or `C:\Users\YourName\Documents`)
   - Click "Start Indexing"
   - Wait for completion (time varies by file count)

2. **Searching**:
   - Go to "Search" tab
   - Enter search term or regex pattern
   - Choose options:
     - **Regex Mode**: Enable for pattern matching
     - **Case Sensitive**: Match exact case
     - **Search Content**: Search inside files (slower but thorough)
   - Apply filters (extensions, size, date)
   - Click "Search"

3. **Export Results**:
   - Click "Export to Markdown"
   - Report saved to `~/.omnisearch/reports/`
   - Open with any Markdown viewer or IDE

### Advanced Usage

#### Regex Examples
- Find all Python class definitions: `^class \w+\(`
- Find TODO comments: `TODO:.*`
- Find email addresses: `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`

#### Extension Filtering
- Code files: `py, js, ts, java, cpp`
- Documents: `md, txt, pdf, docx`
- Config files: `json, yaml, toml, ini`

#### Date Filtering
- Modified in last 7 days: Enter `7` in "Last N days" field
- Combines with other filters for precise results

### Blacklist Management

The "Settings" tab allows you to exclude paths from indexing:

**Default Blacklist** (protects system):
- `Windows`, `Program Files`, `$RECYCLE.BIN`
- `node_modules`, `.git`, `__pycache__`
- `.tmp`, `.cache` files

**Add Custom Patterns**:
- Folder names (e.g., `MyPrivateFolder`)
- Extensions (e.g., `.bak`)

## Architecture

### Database Schema
```
config          → Application settings
blacklist       → Excluded patterns
files           → File metadata (fast queries)
file_contents   → FTS5 virtual table (full-text search)
```

### Processing Flow
```
Discover Files → Diff with Database → Multi-Process Indexing → Update DB
                                    ↓
                              Content Extraction
                                    ↓
                              FTS5 Indexing
```

### Performance Optimizations
- **WAL Mode**: Allows concurrent reads during indexing
- **Batch Commits**: 500 files per transaction
- **Worker Throttling**: Leaves 1-2 CPU cores free
- **Content Size Limit**: 10MB max per file (configurable)

## File Locations

- **Database**: `~/.omnisearch/index.db`
- **Logs**: `~/.omnisearch/logs/omnisearch.log`
- **Reports**: `~/.omnisearch/reports/`

## Troubleshooting

### Indexing is slow
- **Cause**: Large file count or slow disk
- **Solution**: Index specific folders instead of entire drive

### "Permission Denied" errors
- **Cause**: Attempting to access protected system folders
- **Solution**: Already handled gracefully; check logs for details

### Database is too large
- **Cause**: Indexing content of many large files
- **Solution**: Reduce `MAX_CONTENT_SIZE` in `src/core/indexer.py`

### Search returns no results
- **Check**: 
  1. Has indexing completed?
  2. Is "Search Content" enabled?
  3. Are filters too restrictive?

## Development

### Project Structure
```
omnisearch-pro/
├── src/
│   ├── main.py                 # Entry point
│   ├── core/
│   │   ├── database.py         # SQLite manager
│   │   ├── indexer.py          # File crawler
│   │   ├── searcher.py         # Search engine
│   │   └── logger.py           # Logging
│   ├── gui/
│   │   ├── main_window.py      # Main app
│   │   ├── indexing_tab.py     # Indexing UI
│   │   ├── search_tab.py       # Search UI
│   │   └── settings_tab.py     # Settings UI
│   └── utils/
│       ├── file_utils.py       # File operations
│       └── markdown_generator.py  # Report generator
├── requirements.txt
├── build.py
└── README.md
```

### Adding Features

**New File Type Support**:
1. Add extension to `TEXT_EXTENSIONS` in `indexer.py`
2. Optionally add custom content extraction logic

**New Search Filter**:
1. Add UI control in `search_tab.py`
2. Update `_search_worker` to pass new parameter
3. Modify `SearchEngine.search()` and `_add_filters()` in `searcher.py`

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Acknowledgments

- Built with [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- Uses SQLite FTS5 for lightning-fast text search
- Inspired by Everything Search Engine

---

**Version**: 1.0.0  
**Platform**: Windows 11  
**Author**: WeUP Team / oxychain.dev  
**Repository**: https://github.com/oxychain-dev/omnisearch-pro