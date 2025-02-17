#!/usr/bin/env python3
import feedparser
import json
from datetime import datetime
from typing import Any
from pprint import pformat
import logging
import sys
from pathlib import Path
from utils.log_setup import setup_project_logging
from utils.first_rss import dump_rss_feed

# Define directory paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent

# Configure logging
logger = setup_project_logging()

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects"""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def dump_rss_feed():
    """Fetch the RSS feed and dump the entire contents to a file"""
    RSS_FEED_URL = "https://feeds.buzzsprout.com/2194438.rss"
    
    # Create debug directory in project root
    debug_dir = ROOT_DIR / 'debug'
    debug_dir.mkdir(exist_ok=True)
    
    # Parse the feed
    logger.info(f"Fetching RSS feed from: {RSS_FEED_URL}")
    feed = feedparser.parse(RSS_FEED_URL)
    
    # Convert the entire feed to a pretty-printed string
    feed_dump = pformat(feed, indent=2, width=120)
    
    # Write to file
    debug_path = debug_dir / 'debug_rss.txt'
    with open(debug_path, 'w', encoding='utf-8') as f:
        f.write(feed_dump)
    
    logger.info(f"Complete RSS feed details have been written to {debug_path}")

if __name__ == "__main__":
    dump_rss_feed() 