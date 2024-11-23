#!/usr/bin/env python3
import yaml
import logging
import os
import sys
import feedparser
import requests
from pathlib import Path

# Define directory paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent.parent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def load_config() -> dict:
    """Load configuration from config.yaml"""
    try:
        config_path = ROOT_DIR / 'config.yaml'
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise

def get_latest_episode_url() -> tuple[str, str]:
    """Get the latest episode MP3 URL from RSS feed"""
    config = load_config()
    feed_url = config['rss']['feed_url']
    
    # Parse the feed
    feed = feedparser.parse(feed_url)
    
    if not feed.entries:
        raise ValueError("No episodes found in feed")
    
    # Get latest episode
    latest = feed.entries[0]
    
    # Find the MP3 URL in enclosures
    if hasattr(latest, 'enclosures') and latest.enclosures:
        mp3_url = latest.enclosures[0].href
        logger.info(f"Found latest episode: {latest.title}")
        return mp3_url, latest.title
    else:
        raise ValueError("No MP3 URL found in latest episode")

def download_episode(url: str, output_path: Path) -> bool:
    """
    Download episode MP3 file if it doesn't exist
    Returns True if file was downloaded, False if it already existed
    """
    # Check if file already exists
    if output_path.exists():
        logger.info(f"Audio file already exists at {output_path}")
        return False
        
    logger.info(f"Downloading new audio file to {output_path}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Accept': '*/*'
    }
    
    # Stream the download to handle large files
    with requests.get(url, headers=headers, stream=True) as response:
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
    return True

def main():
    """Main function to download episode audio"""
    try:
        # Create debug/audio directory if it doesn't exist
        audio_dir = ROOT_DIR / 'debug' / 'audio'
        audio_dir.mkdir(parents=True, exist_ok=True)
        
        # Get latest episode URL and title from RSS feed
        episode_url, episode_title = get_latest_episode_url()
        logger.info(f"Latest episode URL: {episode_url}")
        
        # Create clean filename from episode title
        clean_filename = f"ep-{episode_title.split('.')[0].split('-')[0].strip()}.mp3"
        output_path = audio_dir / clean_filename
        
        # Download the episode if needed
        if download_episode(episode_url, output_path):
            logger.info("Successfully downloaded new episode")
        else:
            logger.info("Using existing audio file")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 