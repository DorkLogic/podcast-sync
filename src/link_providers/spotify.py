import logging
import base64
import requests
from typing import Optional

logger = logging.getLogger(__name__)

def get_access_token(client_id: str, client_secret: str) -> str:
    """Get access token using client credentials flow"""
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

def get_spotify_podcast_link(episode_number: int, config: dict) -> Optional[str]:
    """Get the Spotify link for the episode using Spotify Web API"""
    try:
        access_token = get_access_token(
            config['spotify']['client_id'],
            config['spotify']['client_secret']
        )
        logger.info("Successfully got access token")
        
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        url = f"https://api.spotify.com/v1/shows/{config['spotify']['show_id']}/episodes"
        logger.info(f"Getting episodes from: {url}")
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        episodes = response.json()
        
        for episode in episodes['items']:
            if episode['name'].startswith(f"{episode_number}."):
                return episode['external_urls']['spotify']
        
        logger.warning(f"Could not find Spotify episode {episode_number}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting Spotify episode: {e}")
        return None 