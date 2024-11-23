#!/usr/bin/env python3
import feedparser
import json
import yaml
import logging
from typing import List, Dict
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def load_config() -> Dict:
    """Load configuration from config.yaml"""
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        sys.exit(1)

def get_episode_data(entry: Dict) -> Dict:
    """Extract relevant episode data from feed entry"""
    return {
        'id': entry.get('id', ''),  # Buzzsprout ID
        'title': entry.get('title', ''),
        'published': entry.get('published', ''),
    }

def get_all_episodes() -> List[Dict]:
    """Fetch and parse all episodes from RSS feed"""
    config = load_config()
    
    try:
        logger.info("Fetching RSS feed...")
        feed = feedparser.parse(config['rss']['feed_url'])
        
        if feed.bozo:
            logger.error(f"RSS feed parsing error: {feed.bozo_exception}")
            sys.exit(1)
            
        if not feed.entries:
            logger.error("No episodes found in feed")
            sys.exit(1)
            
        logger.info(f"Found {len(feed.entries)} episodes")
        
        # Extract episode data from each entry
        episodes = []
        for entry in feed.entries:
            episode = get_episode_data(entry)
            episodes.append(episode)
            
        return episodes
        
    except Exception as e:
        logger.error(f"Failed to parse RSS feed: {str(e)}")
        sys.exit(1)

def save_to_jsonl(episodes: List[Dict]) -> None:
    """Save episodes to episode_ids.jsonl"""
    try:
        with open('episode_ids.jsonl', 'w') as f:
            for episode in episodes:
                json.dump(episode, f)
                f.write('\n')
        logger.info(f"Successfully saved {len(episodes)} episodes to episode_ids.jsonl")
    except Exception as e:
        logger.error(f"Error saving to episode_ids.jsonl: {e}")
        sys.exit(1)

def main():
    """Fetch all episodes and save their IDs to JSONL file"""
    try:
        # Get all episodes
        episodes = get_all_episodes()
        
        # Sort episodes by published date (newest first)
        episodes.sort(key=lambda x: x['published'], reverse=True)
        
        # Save to JSONL file
        save_to_jsonl(episodes)
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 