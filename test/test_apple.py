#!/usr/bin/env python3
import requests
import yaml
import logging
from bs4 import BeautifulSoup
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

def investigate_apple_podcast():
    """Fetch and analyze the Apple Podcast page"""
    config = load_config()
    base_url = config['apple_podcast']['base_url']
    
    # Create debug directory in project root
    debug_dir = ROOT_DIR / 'debug'
    debug_dir.mkdir(exist_ok=True)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    logger.info(f"Fetching Apple Podcast page: {base_url}")
    response = requests.get(base_url, headers=headers)
    
    # Save the raw HTML for inspection
    html_path = debug_dir / 'apple_podcast.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(response.text)
    logger.info(f"Saved raw HTML to {html_path}")
    
    # Try to find any episode-specific metadata
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Look for any script tags that might contain episode data
    scripts = soup.find_all('script')
    
    scripts_path = debug_dir / 'apple_scripts.txt'
    with open(scripts_path, 'w', encoding='utf-8') as f:
        for i, script in enumerate(scripts):
            f.write(f"\n=== Script {i} ===\n")
            f.write(script.string if script.string else str(script))
    logger.info(f"Saved script contents to {scripts_path}")

if __name__ == "__main__":
    investigate_apple_podcast() 