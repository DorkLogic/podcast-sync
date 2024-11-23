#!/usr/bin/env python3
import feedparser
import json
import yaml
import logging
import sys
import time
from datetime import datetime
import subprocess
from typing import Set, Dict
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduled_log_runs.txt'),
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

def load_existing_ids() -> Set[str]:
    """Load existing episode IDs from episode_ids.jsonl"""
    existing_ids = set()
    try:
        with open('episode_ids.jsonl', 'r') as f:
            for line in f:
                episode = json.loads(line.strip())
                existing_ids.add(episode['id'])
        return existing_ids
    except FileNotFoundError:
        logger.warning("episode_ids.jsonl not found. Creating new file.")
        return set()
    except Exception as e:
        logger.error(f"Error loading episode_ids.jsonl: {e}")
        sys.exit(1)

def append_to_jsonl(episode: Dict) -> None:
    """Append new episode to episode_ids.jsonl"""
    try:
        with open('episode_ids.jsonl', 'a') as f:
            json.dump(episode, f)
            f.write('\n')
        logger.info(f"Added new episode {episode['id']} to episode_ids.jsonl")
    except Exception as e:
        logger.error(f"Error appending to episode_ids.jsonl: {e}")
        sys.exit(1)

def check_for_new_episode(config: Dict, existing_ids: Set[str]) -> Dict:
    """Check RSS feed for new episode"""
    try:
        feed = feedparser.parse(config['rss']['feed_url'])
        
        if feed.bozo:
            raise Exception(f"RSS feed parsing error: {feed.bozo_exception}")
            
        if not feed.entries:
            raise Exception("No episodes found in feed")
            
        latest_entry = feed.entries[0]
        latest_id = latest_entry.get('id', '')
        
        if latest_id and latest_id not in existing_ids:
            return {
                'id': latest_id,
                'title': latest_entry.get('title', ''),
                'published': latest_entry.get('published', '')
            }
        return None
        
    except Exception as e:
        logger.error(f"Failed to check RSS feed: {str(e)}")
        return None

def run_podcast_sync() -> bool:
    """Run podcast_sync.py and return True if successful"""
    try:
        logger.info("Running podcast_sync.py...")
        result = subprocess.run([sys.executable, 'podcast_sync.py'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("podcast_sync.py completed successfully")
            return True
        else:
            logger.error(f"podcast_sync.py failed with error:\n{result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error running podcast_sync.py: {e}")
        return False

def wait_until_start(start_datetime: str, timezone_offset: int) -> None:
    """
    Wait until the specified start datetime
    Args:
        start_datetime: Start time in format "YYYY-MM-DD HH:MM:SS"
        timezone_offset: Hours offset from GMT (e.g. -5 for EST)
    """
    try:
        # Parse the configured start time
        start_dt = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
        
        # Create timezone info for configured offset
        configured_tz = pytz.FixedOffset(timezone_offset * 60)  # offset in minutes
        start_dt = configured_tz.localize(start_dt)
        
        # Convert to UTC
        start_dt_utc = start_dt.astimezone(pytz.UTC)
        
        # Get current UTC time
        now_utc = datetime.now(pytz.UTC)
        
        if now_utc < start_dt_utc:
            wait_seconds = (start_dt_utc - now_utc).total_seconds()
            logger.info(f"Current UTC time: {now_utc}")
            logger.info(f"Waiting until {start_dt_utc} UTC to begin checking")
            logger.info(f"This is {start_dt.strftime('%Y-%m-%d %H:%M:%S %z')} in configured timezone (GMT{timezone_offset:+d})")
            time.sleep(wait_seconds)
        else:
            logger.info(f"Start time {start_dt.strftime('%Y-%m-%d %H:%M:%S %z')} has already passed")
            logger.info("Beginning checks immediately...")
            
    except Exception as e:
        logger.error(f"Error handling start datetime: {e}")
        sys.exit(1)

def main():
    """Main function to run scheduled checks"""
    try:
        config = load_config()
        existing_ids = load_existing_ids()
        
        # Wait until start time, passing timezone offset
        wait_until_start(
            config['schedule']['start_datetime'],
            config['schedule']['timezone_offset']
        )
        
        interval_seconds = config['schedule']['interval_minutes'] * 60
        
        while True:
            # Get current time in configured timezone
            now = datetime.now(pytz.UTC).astimezone(
                pytz.FixedOffset(config['schedule']['timezone_offset'] * 60)
            )
            logger.info(f"Checking for new episodes at {now.strftime('%Y-%m-%d %H:%M:%S %z')}...")
            
            new_episode = check_for_new_episode(config, existing_ids)
            
            if new_episode:
                logger.info(f"Found new episode: {new_episode['title']}")
                
                # Run podcast_sync.py
                if run_podcast_sync():
                    # Add new episode to episode_ids.jsonl
                    append_to_jsonl(new_episode)
                    logger.info("Successfully processed new episode. Exiting.")
                    break
                else:
                    logger.error("Failed to process new episode. Will retry next interval.")
            else:
                logger.info("No new episodes found")
                
            logger.info(f"Waiting {config['schedule']['interval_minutes']} minutes until next check...")
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Exiting.")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 