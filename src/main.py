"""
OmniSearch Pro - Enterprise-Grade Local File Search Engine
Version: 1.0.0 (RC1)
Target: Windows 11
Architecture: Local-First / Offline

Main entry point for the application.
"""

import sys
import multiprocessing
from pathlib import Path

# Critical: Freeze support for Windows multiprocessing in .exe
if sys.platform == "win32":
    multiprocessing.freeze_support()

# Ensure proper imports after freeze_support
from src.gui.main_window import OmniSearchApp
from src.core.logger import setup_logger


def main():
    """Application entry point with proper error handling."""
    try:
        # Setup logging before anything else
        logger = setup_logger()
        logger.info("=" * 60)
        logger.info("OmniSearch Pro starting...")
        logger.info("=" * 60)
        
        # Launch GUI
        app = OmniSearchApp()
        app.run()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error in main: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()