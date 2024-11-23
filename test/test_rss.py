#!/usr/bin/env python3
import feedparser
import json
from datetime import datetime
from typing import Any
from pprint import pformat
import os

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects"""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def dump_rss_feed():
    """Fetch the RSS feed and dump the entire contents to a file"""
    RSS_FEED_URL = "https://feeds.buzzsprout.com/2194438.rss"
    
    # Create debug directory if it doesn't exist
    os.makedirs('debug', exist_ok=True)
    
    # Parse the feed
    feed = feedparser.parse(RSS_FEED_URL)
    
    # Convert the entire feed to a pretty-printed string
    feed_dump = pformat(feed, indent=2, width=120)
    
    # Write to file
    with open('debug/debug_rss.txt', 'w', encoding='utf-8') as f:
        f.write(feed_dump)
    
    print(f"Complete RSS feed details have been written to debug/debug_rss.txt")

if __name__ == "__main__":
    dump_rss_feed() 