#!/usr/bin/env python3
import feedparser
import json
from datetime import datetime
from typing import Any
from pprint import pformat

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects"""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def dump_latest_episode():
    """Fetch the RSS feed and dump the latest episode contents to a file"""
    RSS_FEED_URL = "https://feeds.buzzsprout.com/2194438.rss"
    
    # Parse the feed
    feed = feedparser.parse(RSS_FEED_URL)
    
    # Get just the first/latest entry
    if feed.entries:
        latest_episode = feed.entries[0]
        
        # Convert episode to a pretty-printed string
        episode_dump = pformat(latest_episode, indent=2, width=120)
        
        # Write to file
        with open('latest_episode.txt', 'w', encoding='utf-8') as f:
            f.write(episode_dump)
        
        print(f"Latest episode details have been written to latest_episode.txt")
    else:
        print("No episodes found in feed")

if __name__ == "__main__":
    dump_latest_episode() 