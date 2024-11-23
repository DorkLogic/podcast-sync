#!/usr/bin/env python3
import os
import sys
import feedparser
import json
import requests
from datetime import datetime
from typing import Dict
import re
import logging
import yaml
import html
from bs4 import BeautifulSoup
import base64
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug_log.txt'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class PodcastSyncError(Exception):
    """Custom exception for podcast sync errors"""
    pass

def load_config():
    """Load configuration from config.yaml"""
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

def get_apple_podcast_link(episode_number: int) -> tuple[str, str]:
    """
    Get the Apple Podcast link for the episode
    Returns tuple of (short_link, full_link)
    """
    config = load_config()
    base_url = config['apple_podcast']['base_url']
    
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

def generate_slug(title: str) -> str:
    """Generate a URL-friendly slug from the episode title"""
    # Remove episode number from start if present
    title = re.sub(r'^\d+\.\s*', '', title)
    # Convert to lowercase and remove special chars
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    # Replace spaces with hyphens
    slug = re.sub(r'\s+', '-', slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')

def get_episode_number(title: str) -> int:
    """Extract episode number from title"""
    match = re.match(r'^(\d+)\.', title)
    return int(match.group(1)) if match else None

def clean_html(text: str) -> str:
    """Clean HTML content and decode entities"""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    text = html.unescape(text)
    return text.strip()

def extract_spotify_link(content: str) -> str:
    """Extract Spotify link from content HTML"""
    soup = BeautifulSoup(content, 'html.parser')
    spotify_link = soup.find('a', href=lambda h: h and 'spotify.com' in h)
    return spotify_link.get('href') if spotify_link else None

def get_spotify_podcast_link(episode_number: int) -> str:
    """
    Get the Spotify link for the episode using Spotify Web API
    Args:
        episode_number: Episode number to find
    Returns:
        Spotify episode URL if found, None otherwise
    """
    config = load_config()
    
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
        
        url = f"https://api.spotify.com/v1/shows/{config['spotify']['show_id']}/episodes"
        logger.info(f"Getting episodes from: {url}")
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        episodes = response.json()
        
        # Find matching episode by number in name
        for episode in episodes['items']:
            if episode['name'].startswith(f"{episode_number}."):
                return episode['external_urls']['spotify']
        
        logger.warning(f"Could not find Spotify episode {episode_number}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting Spotify episode: {e}")
        return None

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

def get_goodpods_link(episode_number: int, episode_title: str) -> str:
    """
    Get the Goodpods link for the episode
    Args:
        episode_number: Episode number to find
        episode_title: Episode title to use in URL
    Returns:
        Goodpods episode URL
    """
    podcast_id = "274363"  # This is fixed for Market MakeHer podcast
    
    # Generate the URL-friendly title part
    title_slug = generate_slug(episode_title)
    
    # Construct the full URL with episode number and title
    return f"https://goodpods.com/podcasts/market-makeher-podcast-{podcast_id}/{episode_number}-{title_slug}"

def get_latest_episode() -> Dict:
    """Fetch and parse the latest episode from RSS feed"""
    config = load_config()
    
    try:
        feed = feedparser.parse(config['rss']['feed_url'])
        
        if feed.bozo:
            raise PodcastSyncError(f"RSS feed parsing error: {feed.bozo_exception}")
        
        if not feed.entries:
            raise PodcastSyncError("No episodes found in feed")
        
        entry = feed.entries[0]  # Get latest episode
        episode_number = get_episode_number(entry.title)
        
        # Format title to start with "Ep "
        formatted_title = f"Ep {entry.title}" if not entry.title.startswith("Ep ") else entry.title
        
        # Get Apple Podcast link
        apple_podcast_link = get_apple_podcast_link(episode_number) if episode_number else None
        
        # Get Spotify link from content
        content = entry.content[0].value if entry.content else entry.summary
        spotify_link = get_spotify_podcast_link(episode_number) if episode_number else None
        
        # Map RSS feed data to Webflow collection fields
        episode = {
            'fields': {
                'name': formatted_title,  # Episode Title with "EP " prefix
                'slug': generate_slug(entry.title),  # Episode Link (required)
                'episode-number': episode_number,  # Episode - Number
                'episode-description-excerpt': clean_html(entry.summary)[:73],  # Episode - Excerpt (required)
                'description': entry.content[0].value if entry.content else entry.summary,  # Description
                'episode-description': entry.content[0].value if entry.content else entry.summary,  # Episode - Episode Equity
                'episode-featured': True,  # Set featured to true for latest episode
                'episode-color': config['default_episode_color'],  # Set default episode color from config
                'episode-main-image': {
                    "fileId": "6734df80b502809c5c58fb7c",
                    "url": "https://cdn.prod.website-files.com/6581b3472ae6c3c7af188759/6734df80b502809c5c58fb7c_Ep%2062%20Thumbnail%20Market%20MakeHer%20Podcast.png",
                    "alt": None
                }
            }
        }
        
        # Add Apple Podcast link if found
        if apple_podcast_link:
            apple_link_short = apple_podcast_link[0].replace("https://podcasts.apple.com/us/podcast/", "")
            episode['fields']['apple-podcast-link-for-player'] = apple_link_short
            episode['fields']['episode-apple-podcasts-link'] = apple_podcast_link[1]
        
        # Add Spotify link if found
        if spotify_link:
            episode['fields']['episode-spotify-link'] = spotify_link
        
        # Optional fields - add if needed
        if hasattr(entry, 'itunes_duration'):
            episode['fields']['duration'] = entry.itunes_duration
            
        # Get audio URL from enclosure
        audio_url = next((link.href for link in entry.links if link.rel == 'enclosure'), None)
        if audio_url:
            episode['fields']['audio_url'] = audio_url
            
        # Add Goodpods link using episode number and title
        if episode_number:
            goodpods_link = get_goodpods_link(episode_number, entry.title)
            episode['fields']['episode-goodpods-link'] = goodpods_link
        
        return episode
        
    except Exception as e:
        raise PodcastSyncError(f"Failed to parse RSS feed: {str(e)}")

def publish_to_webflow(episode: dict, config: dict) -> dict:
    """
    Create and publish episode in Webflow collection
    """
    # Use v2 API endpoint
    create_url = f'https://api.webflow.com/v2/collections/{config["webflow"]["collection_id"]}/items'
    
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'authorization': f'Bearer {config["webflow"]["api_token"]}',
    }
    
    try:
        # Clean up field names to match Webflow schema
        if 'audio_url' in episode['fields']:
            episode['fields'].pop('audio_url')
            
        # Rename goodpods link to match collection field
        if 'episode-goodpods-link' in episode['fields']:
            episode['fields']['episode-anchor-link'] = episode['fields'].pop('episode-goodpods-link')
        
        # Clean HTML from description fields
        if 'description' in episode['fields']:
            episode['fields']['description'] = clean_html(episode['fields']['description'])
            
        if 'episode-description' in episode['fields']:
            episode['fields']['episode-description'] = clean_html(episode['fields']['episode-description'])
            
        # Valid fields from collection schema
        valid_fields = [
            'name',  # Episode Title (matches slug in collection)
            'slug',  # Episode Link (matches slug in collection)
            'episode-number',  # Episode - Number
            'episode-description-excerpt',  # Episode - Excerpt
            'description',  # Description
            'episode-description',  # Episode - Episode Equity
            'episode-featured',  # Episode - Featured?
            'episode-color',  # Episode - Color
            'episode-main-image',  # Episode - Main Image
            'apple-podcast-link-for-player',  # Apple Podcast Link for Player
            'episode-apple-podcasts-link',  # Episode - Apple Podcasts Link
            'episode-spotify-link',  # Episode - Spotify Link
            'episode-anchor-link',  # Episode - Goodpods Link
        ]
        
        episode['fields'] = {k: v for k, v in episode['fields'].items() 
                           if k in valid_fields}
        
        # Prepare the request body according to v2 API format
        request_body = {
            "fieldData": episode['fields']  # Wrap fields in fieldData property
        }
        
        logger.info("Creating episode in Webflow...")
        logger.debug(f"Request body: {json.dumps(request_body, indent=2)}")
        
        create_response = requests.post(create_url, headers=headers, json=request_body)
        
        # Log the full response details
        logger.debug(f"Response Status: {create_response.status_code}")
        logger.debug(f"Response Headers: {dict(create_response.headers)}")
        logger.debug(f"Response Body: {create_response.text}")
        
        create_response.raise_for_status()
        created_item = create_response.json()
        
        logger.info(f"Episode created successfully with ID: {created_item.get('_id')}")
        
        return created_item
        
    except RequestException as e:
        logger.error(f"Failed to create/publish Webflow episode: {str(e)}")
        if 'create_response' in locals():
            logger.error(f"Response Status: {create_response.status_code}")
            logger.error(f"Response Headers: {dict(create_response.headers)}")
            logger.error(f"Response Body: {create_response.text}")
            logger.error(f"Request body sent: {json.dumps(request_body, indent=2)}")
        raise PodcastSyncError(f"Webflow API error: {str(e)}")

def main():
    """Create and publish the latest episode in Webflow"""
    try:
        config = load_config()
        
        # Get latest episode
        logger.info("Fetching latest episode from RSS feed...")
        episode = get_latest_episode()
        logger.info(f"Found episode: {episode['fields']['name']}")
        
        # Save REST call body for debugging
        with open('test_rest.json', 'w', encoding='utf-8') as f:
            json.dump(episode, f, indent=2)
            
        # Create and publish episode in Webflow
        result = publish_to_webflow(episode, config)
        logger.info(f"Successfully created and published episode with ID: {result.get('_id')}")
        
    except PodcastSyncError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 