#!/usr/bin/env python3
import feedparser
import logging
import subprocess
import time
from pathlib import Path
import yaml
from typing import Optional, Tuple
from datetime import datetime
import sys

# Get directory paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
DEBUG_DIR = ROOT_DIR / 'debug'
MAIN_SCRIPT = SCRIPT_DIR / 'podcast_sync.py'

class RSSPollError(Exception):
    """Custom exception for RSS polling errors"""
    pass

def format_timestamp(timestamp: float) -> str:
    """Convert Unix timestamp to human-readable format"""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def setup_logging(log_file: Path) -> logging.Logger:
    """Set up logging configuration with verbose file logging and terse console output"""
    DEBUG_DIR.mkdir(exist_ok=True)
    
    logger = logging.getLogger('rss_poll')
    logger.setLevel(logging.DEBUG)  # Capture all levels
    
    # Verbose formatter for file
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # Terse formatter for console
    console_formatter = logging.Formatter('%(message)s')
    
    # File handler - verbose logging
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(file_formatter)
    logger.addHandler(fh)
    
    # Console handler - terse logging
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(console_formatter)
    logger.addHandler(ch)
    
    return logger

def load_config():
    """Load configuration from config.yaml"""
    try:
        config_path = ROOT_DIR / 'config.yaml'
        logger.debug(f"Loading config from: {config_path}")
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            logger.debug(f"RSS Feed URL: {config['rss']['feed_url']}")
            return config
    except Exception as e:
        raise RSSPollError(f"Failed to load config: {e}")

def get_last_processed_time(file_path: Path) -> float:
    """Get the timestamp of the last processed episode"""
    try:
        if not file_path.exists():
            logger.debug(f"Last processed file not found at: {file_path}")
            return 0.0
        with open(file_path, 'r') as f:
            timestamp = float(f.read().strip())
            logger.debug(f"Last processed time loaded: {format_timestamp(timestamp)} ({timestamp})")
            return timestamp
    except Exception as e:
        logger.error(f"Error reading last processed time: {e}")
        return 0.0

def save_processed_time(timestamp: float, file_path: Path):
    """Save the timestamp of the processed episode"""
    try:
        DEBUG_DIR.mkdir(exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(str(timestamp))
        logger.debug(f"Saved processed time: {format_timestamp(timestamp)} ({timestamp})")
    except Exception as e:
        raise RSSPollError(f"Failed to save timestamp: {e}")

def check_feed(feed_url: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Check RSS feed for new episodes
    
    Returns:
        Tuple[Optional[float], Optional[str]]: (timestamp, episode_title) if found, (None, None) otherwise
    """
    try:
        logger.debug(f"Polling RSS feed: {feed_url}")
        feed = feedparser.parse(feed_url)
        
        if feed.bozo:
            raise RSSPollError(f"RSS feed parsing error: {feed.bozo_exception}")
            
        if not feed.entries:
            logger.debug("No entries found in feed")
            return None, None

        latest_entry = feed.entries[0]
        logger.debug(f"Latest entry title: {latest_entry.get('title', 'No title')}")
        
        if hasattr(latest_entry, 'published_parsed'):
            timestamp = time.mktime(latest_entry.published_parsed)
            logger.debug(f"Latest entry timestamp: {format_timestamp(timestamp)} ({timestamp})")
            return timestamp, latest_entry.get('title', '')
        
        logger.debug("No valid publish time found in latest entry")
        return None, None
        
    except Exception as e:
        raise RSSPollError(f"Failed to check RSS feed: {e}")

def run_sync_script(logger: logging.Logger) -> bool:
    """Run the podcast sync script"""
    try:
        logger.info("Running podcast sync script...")
        logger.debug(f"Executing: {MAIN_SCRIPT}")
        
        # Use python executable from current environment
        python_exe = "python" if Path.cwd().drive else "python3"
        result = subprocess.run(
            [python_exe, str(MAIN_SCRIPT)],
            check=True,
            capture_output=True,
            text=True
        )
        
        # Log the output
        if result.stdout:
            logger.debug(f"Sync script stdout:\n{result.stdout}")
        if result.stderr:
            logger.debug(f"Sync script stderr:\n{result.stderr}")
            
        logger.info("Podcast sync completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Sync script failed with error:\n{e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error running sync script: {e}")
        return False

def main():
    """Main function to check RSS feed and trigger sync"""
    try:
        # Load config
        config = load_config()
        
        # Set up logging
        log_file = Path(config['rss']['poll_log_file'])
        if not log_file.is_absolute():
            log_file = ROOT_DIR / log_file
        global logger
        logger = setup_logging(log_file)
        
        logger.debug("=== Starting RSS Poll Script ===")
        
        # Get paths
        last_processed_file = Path(config['rss']['last_processed_file'])
        if not last_processed_file.is_absolute():
            last_processed_file = ROOT_DIR / last_processed_file
            
        # Check for new episode
        logger.info("Checking RSS feed for updates...")
        last_time = get_last_processed_time(last_processed_file)
        latest_time, latest_title = check_feed(config['rss']['feed_url'])
        
        if latest_time and latest_time > last_time:
            logger.info(f"New episode detected: {latest_title}")
            logger.debug(f"Last processed: {format_timestamp(last_time)} ({last_time})")
            logger.debug(f"Latest episode: {format_timestamp(latest_time)} ({latest_time})")
            
            if run_sync_script(logger):
                save_processed_time(latest_time, last_processed_file)
                logger.info("Successfully processed new episode")
            else:
                logger.error("Failed to process new episode")
        else:
            if latest_time:
                logger.debug(f"Last processed: {format_timestamp(last_time)} ({last_time})")
                logger.debug(f"Latest episode: {format_timestamp(latest_time)} ({latest_time})")
            logger.info("No new episodes found")
            
    except Exception as e:
        logger.error(f"Error in RSS poll: {e}")
        raise

if __name__ == "__main__":
    logger = None  # Will be initialized in main()
    main() 