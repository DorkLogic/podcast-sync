#!/usr/bin/env python3
import requests
import yaml
import logging
import base64
import json
from pprint import pprint
import sys
from pathlib import Path

# Define directory paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent

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
        raise

def get_access_token(client_id: str, client_secret: str) -> str:
    """
    Get access token using client credentials flow
    """
    # Create Basic auth string by base64 encoding client_id:client_secret
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {'grant_type': 'client_credentials'}
    
    try:
        response = requests.post('https://accounts.spotify.com/api/token', 
                               headers=headers,
                               data=data)
        response.raise_for_status()
        return response.json()['access_token']
    except Exception as e:
        logger.error(f"Error getting access token: {e}")
        if hasattr(response, 'text'):
            logger.error(f"Response: {response.text}")
        raise

def test_spotify_api():
    """Test the Spotify API show episodes endpoint"""
    config = load_config()
    show_id = "5mHdlBVJS7B51OHG93JEVI"
    
    # Create debug directory in project root
    debug_dir = ROOT_DIR / 'debug'
    debug_dir.mkdir(exist_ok=True)
    
    try:
        # First get access token
        access_token = get_access_token(
            config['spotify']['client_id'],
            config['spotify']['client_secret']
        )
        logger.info("Successfully got access token")
        
        # Get show episodes
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        url = f"https://api.spotify.com/v1/shows/{show_id}/episodes"
        logger.info(f"Getting episodes from: {url}")
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Save raw response
        episodes_path = debug_dir / 'spotify_episodes.json'
        with open(episodes_path, 'w', encoding='utf-8') as f:
            json.dump(response.json(), f, indent=2)
            
        # Print first episode details
        episodes = response.json()
        if episodes.get('items'):
            first_episode = episodes['items'][0]
            logger.info("\nLatest Episode:")
            logger.info(f"Name: {first_episode.get('name')}")
            logger.info(f"URL: {first_episode.get('external_urls', {}).get('spotify')}")
            logger.info(f"\nFull response saved to {episodes_path}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

if __name__ == "__main__":
    test_spotify_api() 