from utils.config import load_config
from utils.log_setup import setup_project_logging
from webflow.publisher import publish_episode
import requests
import json
from pathlib import Path
import re
import argparse
import logging
import sys

def setup_logging():
    """Set up logging to both file and console"""
    debug_dir = Path(__file__).parent.parent.parent / 'debug'
    debug_dir.mkdir(exist_ok=True)
    log_file = debug_dir / 'youtube_link_sync_output.txt'
    
    # Create formatters
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_formatter = logging.Formatter('%(message)s')
    
    # Create and configure file handler
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)
    
    # Create and configure console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Get the root logger and configure it
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers and add our new ones
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

def get_all_webflow_episodes(config: dict) -> list:
    """Get all episodes from Webflow"""
    url = f'https://api.webflow.com/v2/collections/{config["webflow"]["episode_collection_id"]}/items'
    
    headers = {
        'accept': 'application/json',
        'authorization': f'Bearer {config["webflow"]["api_token"]}',
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()['items']
    except Exception as e:
        logger.error(f"Failed to get episodes: {e}")
        raise

def update_episode_youtube_link(episode_id: str, youtube_url: str, config: dict) -> None:
    """Update episode with YouTube link in Webflow"""
    url = f'https://api.webflow.com/v2/collections/{config["webflow"]["episode_collection_id"]}/items/{episode_id}'
    
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'authorization': f'Bearer {config["webflow"]["api_token"]}',
    }
    
    data = {
        "fieldData": {
            "episode-youtube-link": youtube_url
        }
    }
    
    try:
        response = requests.patch(url, headers=headers, json=data)
        response.raise_for_status()
        logger.info(f"Successfully updated YouTube link for episode {episode_id}")
    except Exception as e:
        logger.error(f"Failed to update episode YouTube link: {e}")
        raise

def extract_episode_number(title: str) -> int | None:
    """Extract episode number from a video title if it exists"""
    match = re.search(r'Ep(?:isode)?\.?\s*(\d+)', title)
    if match:
        return int(match.group(1))
    return None

def normalize_youtube_url(url: str | None) -> str | None:
    """
    Extract video ID from various YouTube URL formats and return the canonical format.
    Returns None if URL is None or invalid.
    """
    if not url:
        return None
        
    # Common YouTube URL patterns
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([^&?/]+)',
        r'youtube\.com/watch/([^&?/]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            return f"https://www.youtube.com/watch?v={video_id}"
    
    return None

def should_update_url(current_url: str | None, new_url: str) -> bool:
    """
    Determine if the URL needs to be updated based on:
    1. No current URL exists
    2. Current URL is not in the canonical format
    """
    if not current_url:
        return True
        
    normalized_current = normalize_youtube_url(current_url)
    normalized_new = normalize_youtube_url(new_url)
    
    # Update if current URL isn't in canonical format or doesn't match
    return normalized_current != normalized_new

def main():
    parser = argparse.ArgumentParser(description='Update YouTube links for Webflow episodes')
    parser.add_argument('--dry-run', action='store_true', help='Print what would be done without making changes')
    parser.add_argument('--no-publish', action='store_true', help='Skip publishing changes to live site')
    parser.add_argument('--limit', type=int, help='Maximum number of episodes to process')
    parser.add_argument('--batch', action='store_true', help='Process all episodes without asking for confirmation')
    args = parser.parse_args()
    
    logger.info("Starting YouTube link sync process")
    logger.info(f"Arguments: dry_run={args.dry_run}, no_publish={args.no_publish}, limit={args.limit}, batch={args.batch}")
    
    try:
        config = load_config()
        
        # Load YouTube video data
        debug_dir = Path(__file__).parent.parent.parent / 'debug'
        with open(debug_dir / 'youtube_channel_videos.json', 'r', encoding='utf-8') as f:
            youtube_data = json.load(f)
        
        # Get all episodes from Webflow
        webflow_episodes = get_all_webflow_episodes(config)
        
        # Create mapping of episode numbers to YouTube data
        youtube_episodes = {}
        for item in youtube_data['items']:
            title = item['snippet']['title']
            episode_number = extract_episode_number(title)
            if episode_number is not None:
                video_id = item['id']['videoId']
                youtube_episodes[episode_number] = {
                    'title': title,
                    'url': f"https://www.youtube.com/watch?v={video_id}"
                }
        
        # Track episodes needing updates and missing matches
        episodes_to_update = []
        missing_matches = []
        
        for episode in webflow_episodes:
            episode_number = episode['fieldData'].get('episode-number')
            current_url = episode['fieldData'].get('episode-youtube-link')
            
            if episode_number:
                if episode_number in youtube_episodes:
                    youtube_data = youtube_episodes[episode_number]
                    youtube_url = youtube_data['url']
                    
                    if should_update_url(current_url, youtube_url):
                        episodes_to_update.append({
                            'episode': episode,
                            'youtube_data': youtube_data,
                            'current_url': current_url
                        })
                elif not current_url:  # Only track as missing if no current URL
                    missing_matches.append({
                        'number': episode_number,
                        'title': episode['fieldData'].get('name', 'N/A')
                    })
        
        if not episodes_to_update and not missing_matches:
            logger.info("No episodes found needing YouTube link updates")
            return
            
        # Report missing matches first
        if missing_matches:
            logger.info("\nEpisodes missing YouTube matches:")
            logger.info("-" * 50)
            for episode in sorted(missing_matches, key=lambda x: x['number']):
                logger.info(f"Episode {episode['number']}: {episode['title']}")
            logger.info("-" * 50)
            
        # Apply limit if specified
        if args.limit:
            episodes_to_update = episodes_to_update[:args.limit]
            
        if episodes_to_update:
            logger.info(f"\nFound {len(episodes_to_update)} episodes needing updates:")
            
            # Process each episode
            for i, update in enumerate(episodes_to_update, 1):
                episode = update['episode']
                youtube_data = update['youtube_data']
                current_url = update['current_url']
                episode_number = episode['fieldData'].get('episode-number')
                
                logger.info(f"\nProcessing episode {i} of {len(episodes_to_update)}:")
                logger.info("-" * 50)
                logger.info(f"Episode Number: {episode_number}")
                logger.info(f"Webflow Episode Title: {episode['fieldData'].get('name', 'N/A')}")
                logger.info(f"Current YouTube Link: {current_url if current_url else 'None'}")
                logger.info("\nYouTube Data:")
                logger.info(f"Title: {youtube_data['title']}")
                logger.info(f"URL: {youtube_data['url']}")
                logger.info("-" * 50)
                
                if args.dry_run:
                    logger.info("Dry run - no changes made")
                    continue
                    
                if not args.batch:
                    if input("\nProceed with update? (y/n): ").lower() != 'y':
                        logger.info("Update cancelled")
                        break
                
                logger.info(f"Updating episode {episode_number} with YouTube link: {youtube_data['url']}")
                update_episode_youtube_link(episode['id'], youtube_data['url'], config)
                
                if not args.no_publish:
                    logger.info("Attempting to publish episode...")
                    publish_episode(episode['id'], config)
                else:
                    logger.info("Skipping publish step (--no-publish flag used)")
                
                logger.info("Episode update complete")
            
            logger.info("\nAll requested episodes processed")
            
    except Exception as e:
        logger.error(f"Failed to update YouTube links: {e}")
        raise

if __name__ == '__main__':
    main() 