#!/usr/bin/env python3
import os
import sys
import feedparser
import json
import requests
from datetime import datetime
from typing import Dict, Optional
import re
import logging
import yaml
import html
from bs4 import BeautifulSoup
import base64
from requests.exceptions import RequestException
from pathlib import Path
from media.download_episode import get_latest_episode_url, download_episode
from media.transcribe_podcast import transcribe_audio_file, generate_questions
from openai import OpenAI
from ai.classifier import classify_episode_category
from webflow.categories import get_categories
from media.make_thumbnail import create_thumbnail
from webflow.upload_asset import upload_asset
from utils.convert_md_to_html import convert_markdown_to_html

# At the top of the file, after the imports, add:
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
DEBUG_DIR = ROOT_DIR / 'debug'
IMAGES_DIR = DEBUG_DIR / 'images'
THUMBNAILS_DIR = IMAGES_DIR / 'thumbnails'

# Create required directories
DEBUG_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)
THUMBNAILS_DIR.mkdir(exist_ok=True)

# Configure logging to write to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(DEBUG_DIR / 'debug_log.txt'),
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
        config_path = ROOT_DIR / 'config.yaml'
        with open(config_path, 'r') as f:
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
    # Extract episode number if present
    episode_match = re.match(r'^(\d+)\.', title)
    episode_num = episode_match.group(1) if episode_match else ''
    
    # Remove episode number from start if present (temporarily)
    title = re.sub(r'^\d+\.\s*', '', title)
    
    # Convert to lowercase and remove special chars
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    # Replace spaces with hyphens
    slug = re.sub(r'\s+', '-', slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    
    # Add episode prefix back
    if episode_num:
        return f'ep-{episode_num}-{slug.strip("-")}'
    return slug.strip('-')

def create_episode_link(episode_number: int, feed_entries: list) -> str:
    """
    Create a link to a mentioned episode using its number
    Returns full URL to the episode
    """
    # Find the episode in feed entries
    for entry in feed_entries:
        if entry.title.startswith(f"{episode_number}."):
            slug = generate_slug(entry.title)
            return f"https://www.marketmakeherpodcast.com/episode/{slug}"
    return None

def process_episode_mentions(description: str, feed_entries: list) -> str:
    """
    Process episode mentions in description and convert them to hyperlinks
    and truncate everything after
    """
    # Pattern to match the Episodes mentioned section with HTML tags
    mentions_pattern = r'(<b>Episodes mentioned:<br /></b>.*?</p>)'
    
    # Find the episodes mentioned section
    match = re.search(mentions_pattern, description, flags=re.DOTALL)
    if match:
        # Get everything before the episodes section
        content_before = description[:match.start()]
        
        episodes_section = match.group(1)
        # Process the episodes to add hyperlinks
        def replace_episodes(section_match):
            episodes_text = section_match.group(1)
            # Split on <br /> to get individual episodes
            episodes = episodes_text.split('<br />')
            
            processed_episodes = []
            for episode in episodes:
                # Match episode number and title
                ep_match = re.match(r'(\d+)\.\s*(.*?)(?:\xa0)?$', episode.strip())
                if ep_match:
                    episode_num = int(ep_match.group(1))
                    episode_text = episode.strip()
                    
                    # Get the full URL for this episode
                    episode_url = create_episode_link(episode_num, feed_entries)
                    if episode_url:
                        processed_episodes.append(f'<a href="{episode_url}">{episode_text}</a>')
                    else:
                        processed_episodes.append(episode_text)
            
            # Reconstruct the section with hyperlinks
            return f'<b>Episodes mentioned:<br /></b>{("<br />".join(processed_episodes))}</p>'

        # Process the episodes section
        processed_section = re.sub(r'<b>Episodes mentioned:<br /></b>(.*?)</p>', 
                                 replace_episodes, 
                                 episodes_section, 
                                 flags=re.DOTALL)
        
        # Return everything before plus the processed episodes section
        return content_before + processed_section
    
    # If no episodes section found, return original description
    return description

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

def upload_image_to_webflow(image_path: Path, config: dict, alt_text: str) -> dict:
    """
    Upload an image to Webflow and return the image asset data
    
    Args:
        image_path: Path to the image file
        config: Application configuration containing Webflow settings
        alt_text: Alt text for the image
        
    Returns:
        Dict containing fileId, url, and alt text for the image
    """
    try:
        return upload_asset(image_path, config, alt_text)
    except Exception as e:
        logger.error(f"Failed to upload image to Webflow: {e}")
        raise

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
        
        # Format title to use "Ep N:" format
        title_without_number = re.sub(r'^\d+\.\s*', '', entry.title)
        formatted_title = f"Ep {episode_number}: {title_without_number}" if episode_number else entry.title
        
        # Get Apple Podcast link
        apple_podcast_link = get_apple_podcast_link(episode_number) if episode_number else None
        
        # Get full content and process it
        full_content = entry.content[0].value if entry.content else entry.summary
        processed_content = process_episode_mentions(full_content, feed.entries)
        
        # Get Spotify link
        spotify_link = get_spotify_podcast_link(episode_number) if episode_number else None
        
        # Map RSS feed data to Webflow collection fields
        episode = {
            'fields': {
                'name': formatted_title,  # Episode Title with "Ep N:" format
                'slug': generate_slug(entry.title),  # Episode Link (required)
                'episode-number': episode_number,  # Episode - Number
                'episode-description-excerpt': clean_html(entry.summary)[:73],  # Episode - Excerpt (required)
                'description': processed_content,  # Description
                'episode-description': processed_content,  # Episode - Episode Equity
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
        
        # Create thumbnail before returning episode
        try:
            logger.info("Creating episode thumbnail...")
            background_path = IMAGES_DIR / 'default_episode_background.png'
            if not background_path.exists():
                logger.error(f"Background image not found at {background_path}")
                raise PodcastSyncError("Background image for thumbnail not found")
                
            thumbnail_filename = f"{episode['fields']['slug']}{background_path.suffix}"
            thumbnail_path = THUMBNAILS_DIR / thumbnail_filename
            
            # Create thumbnail with episode number formatted as "EP XX"
            thumbnail_text = f"EP {episode_number}"
            created_thumbnail_path = create_thumbnail(
                text=thumbnail_text,
                input_image_path=str(background_path),
                output_name=episode['fields']['slug'],
                font_size=75,
                font_color="#FFFFFF"
            )
            logger.info(f"Thumbnail created at {thumbnail_path}")
            
            # Upload thumbnail to Webflow
            logger.info("Uploading thumbnail to Webflow...")
            image_data = upload_image_to_webflow(
                Path(created_thumbnail_path), 
                config,
                alt_text=episode['fields']['name']  # Use episode name as alt text
            )
            
            # Only update episode-main-image if upload succeeded
            if image_data:
                episode['fields']['episode-main-image'] = image_data
                logger.info(f"Thumbnail uploaded successfully with ID: {image_data['fileId']}")
            else:
                logger.error("Failed to get image data from Webflow upload")
                raise PodcastSyncError("Failed to upload thumbnail to Webflow")
                
        except Exception as e:
            logger.error(f"Failed to create or upload thumbnail: {e}")
            raise PodcastSyncError(f"Thumbnail processing failed: {str(e)}")

        return episode
        
    except Exception as e:
        raise PodcastSyncError(f"Failed to parse RSS feed: {str(e)}")

def publish_to_webflow(episode: dict, config: dict, debug_mode: bool = False) -> Optional[dict]:
    """
    Create and publish episode in Webflow collection
    If debug_mode is True, only saves request body without making API call
    """
    # Use v2 API endpoint with updated collection_id reference
    create_url = f'https://api.webflow.com/v2/collections/{config["webflow"]["episode_collection_id"]}/items'
    
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
            
        # Valid fields from collection schema - UPDATED to include jessie-s-questions
        valid_fields = [
            'name',  # Episode Title (matches slug in collection)
            'slug',  # Episode Link (matches slug in collection)
            'episode-number',  # Episode - Number
            'episode-description-excerpt',  # Episode - Excerpt
            'description',  # Description
            'episode-transcript',  # Episode - Transcript
            'jessie-s-questions',  # Jessie's Questions (added this)
            'episode-category',  # Episode - Category
            'episode-featured',  # Episode - Featured?
            'episode-color',  # Episode - Color
            'episode-main-image',  # Episode - Main Image
            'apple-podcast-link-for-player',  # Apple Podcast Link for Player
            'episode-apple-podcasts-link',  # Episode - Apple Podcasts Link
            'episode-spotify-link',  # Episode - Spotify Link
            'episode-anchor-link',  # Episode - Goodpods Link
        ]
        
        # Only include valid fields in the request
        filtered_fields = {k: v for k, v in episode['fields'].items() 
                         if k in valid_fields}
        
        # Log fields before filtering
        logger.debug(f"Fields before filtering: {list(episode['fields'].keys())}")
        logger.debug(f"Fields after filtering: {list(filtered_fields.keys())}")
        
        # Prepare the request body according to v2 API format
        request_body = {
            "fieldData": filtered_fields
        }
        
        # Create network debug directory if it doesn't exist
        network_debug_dir = DEBUG_DIR / 'network'
        network_debug_dir.mkdir(exist_ok=True)
        
        # Save request body to debug file
        debug_file = network_debug_dir / 'webflow_publish_request.json'
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(request_body, f, indent=2)
        logger.info(f"Saved request body to {debug_file}")
        
        if debug_mode:
            logger.info("Debug mode: Skipping API call")
            return None
            
        # Make actual API call if not in debug mode
        logger.info("Creating episode in Webflow...")
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
        if not debug_mode and 'create_response' in locals():
            logger.error(f"Response Status: {create_response.status_code}")
            logger.error(f"Response Headers: {dict(create_response.headers)}")
            logger.error(f"Response Body: {create_response.text}")
            logger.error(f"Request body sent: {json.dumps(request_body, indent=2)}")
        raise PodcastSyncError(f"Webflow API error: {str(e)}")

def get_category_id(category_name: str, config: dict) -> str:
    """Get category ID from category name"""
    try:
        # Get categories collection
        url = f'https://api.webflow.com/v2/collections/{config["webflow"]["category_collection_id"]}/items'
        
        headers = {
            'accept': 'application/json',
            'authorization': f'Bearer {config["webflow"]["api_token"]}',
            'accept-version': '2.0.0'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Find matching category
        for item in response.json().get('items', []):
            if item['fieldData'].get('name') == category_name:
                return item['id']
                
        raise PodcastSyncError(f"Category not found: {category_name}")
        
    except Exception as e:
        logger.error(f"Error getting category ID: {e}")
        raise

def main(debug_mode: bool = False):
    """Create and publish the latest episode in Webflow"""
    try:
        config = load_config()
        
        # Get latest episode
        logger.info("Fetching latest episode from RSS feed...")
        episode = get_latest_episode()
        logger.info(f"Found episode: {episode['fields']['name']}")
        
        # Download audio and get transcription
        try:
            # Download audio
            episode_url, episode_title = get_latest_episode_url()
            audio_dir = DEBUG_DIR / 'audio'
            audio_dir.mkdir(exist_ok=True)
            
            clean_filename = f"ep-{episode_title.split('.')[0].split('-')[0].strip()}.mp3"
            output_path = audio_dir / clean_filename
            
            logger.info(f"Downloading episode audio to {output_path}")
            download_episode(episode_url, output_path)
            logger.info("Audio download complete")

            # Initialize OpenAI client and get transcription
            logger.info("Starting audio transcription...")
            client = OpenAI(api_key=config['openai']['api_key'])
            transcript = transcribe_audio_file(client, str(output_path), config)
            
            # Generate questions and answers if they don't exist
            question_file_path = audio_dir / f"{output_path.stem}-questions.md"
            if not question_file_path.exists():
                logger.info("Generating questions and answers...")
                generate_questions(client, transcript, question_file_path)
                logger.info(f"Questions and answers saved to {question_file_path}")
            else:
                logger.info(f"Using existing questions from {question_file_path}")

            # Convert questions to HTML and add to episode fields
            if question_file_path.exists():
                logger.info("Converting questions from markdown to HTML...")
                try:
                    with open(question_file_path, 'r', encoding='utf-8') as f:
                        questions_md = f.read()
                    
                    # Split into individual Q&A pairs
                    qa_pairs = questions_md.strip().split('\n\n')
                    
                    # Convert to HTML divs instead of list items
                    html_items = []
                    for pair in qa_pairs:
                        if pair.strip():
                            q, a = pair.split('\nA: ')
                            q = q.replace('Q: ', '')
                            html_items.append(
                                f'<div class="qa-item">'
                                f'<div><strong>Q:</strong> {q}</div>'
                                f'<div><strong>A:</strong> {a}</div>'
                                f'</div>'
                            )
                    
                    # Wrap in container div
                    questions_html = (
                        '<div class="qa-container">'
                        f'{" ".join(html_items)}'
                        '</div>'
                    )
                    
                    # Add HTML questions to episode fields
                    episode['fields']['jessie-s-questions'] = questions_html
                    logger.info("HTML questions added to episode fields")
                except Exception as e:
                    logger.error(f"Failed to convert questions to HTML: {e}")
                    raise
            else:
                logger.error(f"Questions markdown file not found at {question_file_path}")

            # Convert transcript markdown to HTML before adding to episode fields
            transcript_md_path = output_path.with_suffix('.md')
            if transcript_md_path.exists():
                logger.info("Converting transcript from markdown to HTML...")
                try:
                    transcript_html = convert_markdown_to_html(transcript_md_path)
                    # Add HTML transcript to episode fields
                    episode['fields']['episode-transcript'] = transcript_html
                    logger.info("HTML transcript added to episode fields")
                except Exception as e:
                    logger.error(f"Failed to convert transcript to HTML: {e}")
                    raise
            else:
                logger.error(f"Transcript markdown file not found at {transcript_md_path}")

            # Get category names from Webflow
            logger.info("Getting categories from Webflow...")
            categories = get_categories(config)
            
            # Classify episode using episode name instead of transcript
            logger.info("Classifying episode...")
            category = classify_episode_category(
                episode['fields']['name'],  # Use episode name instead of transcript
                categories, 
                config
            )
            logger.info(f"Episode classified as: {category}")
            
            # Get category ID and add to episode fields
            category_id = get_category_id(category, config)
            episode['fields']['episode-category'] = category_id
            logger.info(f"Added category ID: {category_id}")

        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            # Continue with episode creation even if audio processing fails
        
        # Save REST call body for debugging
        debug_file = ROOT_DIR / 'test_rest.json'
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(episode, f, indent=2)
            
        # Create and publish episode in Webflow
        result = publish_to_webflow(episode, config, debug_mode=debug_mode)
        if debug_mode:
            logger.info("Debug mode: Request body saved without making API call")
        else:
            logger.info(f"Successfully created and published episode with ID: {result.get('_id')}")
        
    except PodcastSyncError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Check if debug mode is requested via command line argument
    debug_mode = "--debug" in sys.argv
    main(debug_mode=debug_mode) 