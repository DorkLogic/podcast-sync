#!/usr/bin/env python3
import requests
import yaml
import logging
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config():
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def investigate_spotify():
    config = load_config()
    base_url = config['spotify_podcast']['base_url']
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    logger.info(f"Fetching Spotify page: {base_url}")
    response = requests.get(base_url, headers=headers)
    
    # Save the raw HTML for inspection
    with open('spotify_podcast.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    logger.info("Saved raw HTML to spotify_podcast.html")
    
    # Try to find any script tags that might contain episode data
    soup = BeautifulSoup(response.text, 'html.parser')
    scripts = soup.find_all('script')
    
    with open('spotify_scripts.txt', 'w', encoding='utf-8') as f:
        for i, script in enumerate(scripts):
            f.write(f"\n=== Script {i} ===\n")
            f.write(script.string if script.string else str(script))
    logger.info("Saved script contents to spotify_scripts.txt")

if __name__ == "__main__":
    investigate_spotify() 