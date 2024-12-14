import logging
import sys
from pathlib import Path

def setup_project_logging():
    """Configure and return logger for the podcast sync project"""
    # Create debug directory if it doesn't exist
    debug_dir = Path('debug')
    debug_dir.mkdir(exist_ok=True)

    # Configure logging to write to both file and console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(debug_dir / 'debug_log.txt'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__) 