#!/usr/bin/env python3
import feedparser
import json
import yaml
import logging
import sys
from pathlib import Path

# Define directory paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
DEBUG_DIR = ROOT_DIR / 'debug'

# Create debug directory if it doesn't exist
DEBUG_DIR.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from config.yaml"""
    try:
        config_path = ROOT_DIR / 'config.yaml'
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        sys.exit(1)

def main():
    """Fetch and dump RSS feed contents"""
    config = load_config()
    
    try:
        feed = feedparser.parse(config['rss']['feed_url'])
        
        # Save feed contents to debug file
        debug_path = DEBUG_DIR / 'debug_rss.txt'
        with open(debug_path, 'w', encoding='utf-8') as f:
            json.dump(feed, f, indent=2, default=str)
            
        logger.info(f"RSS feed contents saved to {debug_path}")
        
    except Exception as e:
        logger.error(f"Error processing RSS feed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 