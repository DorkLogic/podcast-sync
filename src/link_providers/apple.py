import logging
import requests
from typing import Optional, Tuple
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def get_apple_podcast_link(episode_number: int, base_url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Get the Apple Podcast link for the episode
    Args:
        episode_number: Episode number to find
        base_url: Base URL for the podcast on Apple Podcasts
    Returns:
        Tuple of (short_link, full_link)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        scripts = soup.find_all('script')
        
        # Find the script with workExample data
        for script in scripts:
            if script.string and '"workExample"' in script.string:
                data = json.loads(script.string)
                # Find the matching episode
                for example in data.get('workExample', []):
                    if example.get('name', '').startswith(f"{episode_number}."):
                        full_url = example['url']
                        # Create short URL by removing base
                        short_url = full_url.replace('https://podcasts.apple.com/us/podcast/', '')
                        return short_url, full_url
                        
        logger.warning(f"Could not find episode {episode_number} in Apple Podcast data")
        return None, None
        
    except Exception as e:
        logger.error(f"Error getting Apple Podcast link: {e}")
        return None, None 