#!/usr/bin/env python3
import sys
import os
import logging
import argparse
from pathlib import Path
import requests
import yaml
import feedparser
import re
import time
from typing import List, Dict, Set
from openai import OpenAI
from media.download_episode import download_episode
from ai.transcribe_podcast import transcribe_audio_file, generate_questions
from utils.convert_md_to_html import convert_markdown_to_html
from utils.feed_parser import get_latest_episode
from webflow.publisher import publish_site
from utils.text import sanitize_filename
from utils.optimize_image import optimize_image
from media.make_thumbnail import create_thumbnail
from webflow.upload_asset import upload_asset
from ai.create_excerpt import create_excerpt
from ai.classifier import classify_episode_category
from webflow.categories import get_categories
from podcast_sync import (
    create_episode_in_webflow, 
    get_apple_podcast_link,
    get_spotify_podcast_link,
    get_goodpods_link,
    generate_episode_excerpt,
    get_category_id
)

# Setup paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
DEBUG_DIR = ROOT_DIR / 'debug'
AUDIO_DIR = DEBUG_DIR / 'audio'
IMAGES_DIR = DEBUG_DIR / 'images'
THUMBNAILS_DIR = IMAGES_DIR / 'thumbnails'
ASSETS_DIR = ROOT_DIR / 'assets'
ASSETS_IMAGES_DIR = ASSETS_DIR / 'images'
ASSETS_FONTS_DIR = ASSETS_DIR / 'fonts'

# Ensure directories exist
DEBUG_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)
THUMBNAILS_DIR.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(DEBUG_DIR / 'retro_sync_log.txt'),
        logging.StreamHandler(sys.stdout)
    ]
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
        sys.exit(1)

def get_episodes_without_transcript(config: dict) -> list:
    """Get all episodes that don't have transcripts from Webflow"""
    url = f'https://api.webflow.com/v2/collections/{config["webflow"]["episode_collection_id"]}/items'
    
    headers = {
        'accept': 'application/json',
        'authorization': f'Bearer {config["webflow"]["api_token"]}',
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        episodes = response.json()['items']
        
        # Filter episodes without transcripts
        episodes_without_transcript = [
            episode for episode in episodes
            if not episode['fieldData'].get('episode-transcript')
        ]
        
        # Sort by episode number (descending)
        episodes_without_transcript.sort(
            key=lambda x: int(x['fieldData'].get('episode-number', 0)), 
            reverse=True
        )
        
        return episodes_without_transcript
        
    except Exception as e:
        logger.error(f"Failed to get episodes: {e}")
        raise

def update_episode_transcript(episode_id: str, transcript_html: str, config: dict) -> None:
    """Update episode with transcript in Webflow"""
    url = f'https://api.webflow.com/v2/collections/{config["webflow"]["episode_collection_id"]}/items/{episode_id}'
    
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'authorization': f'Bearer {config["webflow"]["api_token"]}',
    }
    
    data = {
        "fieldData": {
            "episode-transcript": transcript_html
        }
    }
    
    try:
        response = requests.patch(url, headers=headers, json=data)
        response.raise_for_status()
        logger.info(f"Successfully updated transcript for episode {episode_id}")
    except Exception as e:
        logger.error(f"Failed to update episode transcript: {e}")
        raise

def get_episode_audio_url(episode_number: str, config: dict) -> str:
    """Get episode audio URL from RSS feed first, fallback to BuzzSprout API"""
    # Try RSS feed first
    try:
        logger.info("Attempting to get audio URL from RSS feed...")
        feed = feedparser.parse(config['rss']['feed_url'])
        
        for entry in feed.entries:
            if entry.title.startswith(f"{episode_number}."):
                # Get audio URL from enclosure
                audio_url = next((link.href for link in entry.links if link.rel == 'enclosure'), None)
                if audio_url:
                    logger.info(f"Found audio URL in RSS feed: {audio_url}")
                    return audio_url
        
        logger.warning("Episode not found in RSS feed, trying BuzzSprout API...")
    except Exception as e:
        logger.warning(f"Failed to get audio URL from RSS feed: {e}")
    
    # Fallback to BuzzSprout API
    url = f'https://www.buzzsprout.com/api/{config["buzzSprout"]["podcast_id"]}/episodes'
    
    headers = {
        'Authorization': f'Token token={config["buzzSprout"]["api_key"]}',
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        episodes = response.json()
        
        # Find matching episode by title starting with episode number
        for episode in episodes:
            if episode['title'].startswith(f"{episode_number}."):
                logger.info(f"Found audio URL in BuzzSprout API: {episode['audio_url']}")
                return episode['audio_url']
                
        raise Exception(f"Episode {episode_number} not found in BuzzSprout or RSS feed")
        
    except Exception as e:
        logger.error(f"Failed to get episode audio URL: {e}")
        raise

def process_episode(episode: dict, config: dict) -> None:
    """Process a single episode to add transcript and questions"""
    episode_number = episode['fieldData'].get('episode-number')
    episode_id = episode['id']
    
    try:
        # Get audio URL
        logger.info(f"Getting audio URL for episode {episode_number}...")
        audio_url = get_episode_audio_url(episode_number, config)
        
        # Download full audio file
        logger.info("Downloading full audio file...")
        audio_path = AUDIO_DIR / f"ep-{episode_number}.mp3"
        
        # Use the existing download_episode function to get the full file
        download_episode(audio_url, audio_path)
        
        original_size = audio_path.stat().st_size / (1024 * 1024)
        logger.info(f"Downloaded full episode: {original_size:.2f}MB")
        
        # Transcribe the full audio file (speed-up optimization will be applied automatically)
        logger.info("Transcribing audio...")
        client = OpenAI(
            api_key=config['openai']['api_key'],
            timeout=60.0,  # Default 60 second timeout
            max_retries=2  # Retry failed requests up to 2 times
        )
        transcript = transcribe_audio_file(client, str(audio_path), config)
        
        # Generate questions and answers
        question_file_path = audio_path.with_suffix('.md').with_stem(f"{audio_path.stem}-questions")
        if not question_file_path.exists():
            logger.info("Generating questions and answers...")
            generate_questions(client, transcript, question_file_path)
            logger.info(f"Questions and answers saved to {question_file_path}")
        else:
            logger.info(f"Using existing questions from {question_file_path}")
        
        # Convert transcript and questions to HTML
        transcript_md_path = audio_path.with_suffix('.md')
        updates = {}
        
        if transcript_md_path.exists():
            logger.info("Converting transcript to HTML...")
            transcript_html = convert_markdown_to_html(transcript_md_path)
            updates["episode-transcript"] = transcript_html
        
        if question_file_path.exists():
            logger.info("Converting questions from markdown to HTML...")
            try:
                with open(question_file_path, 'r', encoding='utf-8') as f:
                    questions_md = f.read()
                
                # Split into individual Q&A pairs
                qa_pairs = questions_md.strip().split('\n\n')
                
                # Convert to HTML divs
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
                
                updates["jessie-s-questions"] = questions_html
                logger.info("HTML questions prepared for update")
            except Exception as e:
                logger.error(f"Failed to convert questions to HTML: {e}")
                raise
        
        # Update episode with transcript and questions
        if updates:
            logger.info("Updating episode with transcript and questions...")
            update_episode_content(episode_id, updates, config)
            
            # Clean up audio file
            audio_path.unlink()
            logger.info(f"Processed episode {episode_number} successfully")
        else:
            logger.error("No content to update")
            
    except Exception as e:
        logger.error(f"Failed to process episode {episode_number}: {e}")
        # Clean up audio file if it exists
        if 'audio_path' in locals() and audio_path.exists():
            audio_path.unlink()
        raise

def update_episode_content(episode_id: str, updates: dict, config: dict) -> None:
    """Update episode with multiple fields in Webflow and publish changes"""
    url = f'https://api.webflow.com/v2/collections/{config["webflow"]["episode_collection_id"]}/items/{episode_id}'
    
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'authorization': f'Bearer {config["webflow"]["api_token"]}',
    }
    
    data = {
        "fieldData": updates
    }
    
    try:
        # Update the episode content
        response = requests.patch(url, headers=headers, json=data)
        response.raise_for_status()
        logger.info(f"Successfully updated episode {episode_id}")
        
        # Publish the changes
        logger.info("Publishing changes to live site...")
        publish_site(config)
        logger.info("Changes published successfully")
        
    except Exception as e:
        logger.error(f"Failed to update episode content: {e}")
        raise

def get_all_rss_episodes(config: dict) -> List[Dict]:
    """Get all episodes from RSS feed"""
    try:
        logger.info("Fetching all episodes from RSS feed...")
        feed = feedparser.parse(config['rss']['feed_url'])
        
        if feed.bozo:
            raise Exception(f"RSS feed parsing error: {feed.bozo_exception}")
            
        if not feed.entries:
            raise Exception("No episodes found in feed")
            
        episodes = []
        for entry in feed.entries:
            # Extract episode number from title
            match = re.match(r'^(\d+)\.', entry.title)
            if match:
                episode_number = int(match.group(1))
                episodes.append({
                    'number': episode_number,
                    'entry': entry
                })
        
        logger.info(f"Found {len(episodes)} episodes in RSS feed")
        return episodes
        
    except Exception as e:
        logger.error(f"Failed to get RSS episodes: {e}")
        raise

def get_all_webflow_episodes(config: dict) -> List[Dict]:
    """Get all episodes from Webflow"""
    url = f'https://api.webflow.com/v2/collections/{config["webflow"]["episode_collection_id"]}/items'
    
    headers = {
        'accept': 'application/json',
        'authorization': f'Bearer {config["webflow"]["api_token"]}',
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        episodes = response.json()['items']
        logger.info(f"Found {len(episodes)} episodes in Webflow")
        return episodes
    except Exception as e:
        logger.error(f"Failed to get Webflow episodes: {e}")
        raise

def find_missing_episodes(rss_episodes: List[Dict], webflow_episodes: List[Dict]) -> List[Dict]:
    """Find episodes that exist in RSS but not in Webflow"""
    # Get episode numbers from Webflow
    webflow_numbers = set()
    for episode in webflow_episodes:
        episode_num = episode['fieldData'].get('episode-number')
        if episode_num:
            webflow_numbers.add(int(episode_num))
    
    # Find missing episodes
    missing_episodes = []
    for rss_episode in rss_episodes:
        if rss_episode['number'] not in webflow_numbers:
            missing_episodes.append(rss_episode)
    
    # Sort by episode number (ascending - oldest first)
    missing_episodes.sort(key=lambda x: x['number'])
    
    logger.info(f"Found {len(missing_episodes)} missing episodes: {[e['number'] for e in missing_episodes]}")
    return missing_episodes

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

def clean_html(text: str) -> str:
    """Clean HTML content and decode entities"""
    import html
    from bs4 import BeautifulSoup
    # Remove HTML tags
    soup = BeautifulSoup(text, 'html.parser')
    text = soup.get_text()
    # Decode HTML entities
    text = html.unescape(text)
    return text.strip()

def clean_description(content: str) -> str:
    """Clean up the description by removing the support link and everything after it"""
    support_link = '<p><a href="https://www.paypal.com/donate/?hosted_button_id=Y23G2PFDRHTJS" rel="payment">Support the show</a></p>'
    index = content.find(support_link)
    if index != -1:
        return content[:index].rstrip()
    return content

def create_episode_from_rss(entry: dict, episode_number: int, config: dict) -> dict:
    """Create episode data structure from RSS entry"""
    try:
        # Format title to use "Ep N:" format
        title_without_number = re.sub(r'^\d+\.\s*', '', entry.title)
        formatted_title = f"Ep {episode_number}: {title_without_number}"
        
        # Get full content and clean it
        full_content = entry.content[0].value if entry.content else entry.summary
        cleaned_content = clean_description(full_content)
        
        # Create episode dict
        episode = {
            'fields': {
                'name': formatted_title,
                'slug': generate_slug(entry.title),
                'episode-number': episode_number,
                'description': cleaned_content,
                'episode-description': cleaned_content,
                'episode-description-excerpt': clean_html(entry.summary)[:73],
                'episode-featured': False,  # Not featured for backfilled episodes
                'episode-color': config['default_episode_color'],
            }
        }
        
        return episode
        
    except Exception as e:
        logger.error(f"Failed to create episode from RSS entry: {e}")
        raise

def process_missing_episode(rss_episode: dict, config: dict) -> None:
    """Process a missing episode - create it in Webflow with all content"""
    entry = rss_episode['entry']
    episode_number = rss_episode['number']
    
    logger.info(f"Processing missing episode {episode_number}: {entry.title}")
    
    try:
        # Create base episode structure
        episode = create_episode_from_rss(entry, episode_number, config)
        
        # Add Apple Podcast link
        short_link, full_link = get_apple_podcast_link(episode_number)
        if full_link:
            episode['fields']['episode-apple-podcasts-link'] = full_link
            if short_link:
                episode['fields']['apple-podcast-link-for-player'] = short_link
        
        # Add Spotify link
        spotify_link = get_spotify_podcast_link(episode_number)
        if spotify_link:
            episode['fields']['episode-spotify-link'] = spotify_link
        
        # Add Goodpods link
        goodpods_link = get_goodpods_link(episode_number, entry.title)
        episode['fields']['episode-anchor-link'] = goodpods_link
        
        # Create and upload thumbnail
        try:
            logger.info("Creating episode thumbnail...")
            background_path = ASSETS_IMAGES_DIR / 'default_episode_background.png'
            if not background_path.exists():
                logger.error(f"Background image not found at {background_path}")
                raise Exception("Background image for thumbnail not found")
                
            # Create filename and sanitize it
            base_filename = f"{episode['fields']['slug']}{background_path.suffix}"
            thumbnail_filename = sanitize_filename(base_filename)
            thumbnail_path = THUMBNAILS_DIR / thumbnail_filename
            
            # Create thumbnail with episode number
            thumbnail_text = f"{episode_number}"
            font_path = ASSETS_FONTS_DIR / "AbrilFatface-Regular.ttf"
            
            # Create large version first
            large_base_filename = f"{episode['fields']['slug']}_large{background_path.suffix}"
            large_thumbnail_filename = sanitize_filename(large_base_filename)
            large_thumbnail_path = THUMBNAILS_DIR / large_thumbnail_filename
            large_thumbnail_path = create_thumbnail(
                text=thumbnail_text,
                input_image_path=str(background_path),
                output_name=os.path.splitext(large_thumbnail_filename)[0],
                font_size=225,
                font_color="#FFFFFF",
                font_path=str(font_path),
                position=(420, 720)
            )
            
            # Optimize the large thumbnail
            optimized_path = optimize_image(
                input_path=large_thumbnail_path,
                output_path=thumbnail_path,
                max_size=(540, 540),
                quality=85,
                format='PNG'
            )
            
            # Upload to Webflow
            image_data = upload_asset(
                Path(optimized_path), 
                config,
                alt_text=episode['fields']['name']
            )
            
            if image_data:
                episode['fields']['episode-main-image'] = image_data
                logger.info(f"Thumbnail uploaded successfully")
                
        except Exception as e:
            logger.error(f"Failed to create or upload thumbnail: {e}")
            # Continue without thumbnail
        
        # Download audio and get transcription
        try:
            # Get audio URL
            audio_url = get_episode_audio_url(str(episode_number), config)
            
            # Download full audio file
            logger.info("Downloading full audio file...")
            audio_path = AUDIO_DIR / f"ep-{episode_number}.mp3"
            
            # Use the existing download_episode function to get the full file
            download_episode(audio_url, audio_path)
            
            original_size = audio_path.stat().st_size / (1024 * 1024)
            logger.info(f"Downloaded full episode: {original_size:.2f}MB")
            
            # Transcribe
            logger.info("Transcribing audio...")
            client = OpenAI(
                api_key=config['openai']['api_key'],
                timeout=60.0,  # Default 60 second timeout
                max_retries=2  # Retry failed requests up to 2 times
            )
            transcript = transcribe_audio_file(client, str(audio_path), config)
            
            # Generate questions
            question_file_path = audio_path.with_suffix('.md').with_stem(f"{audio_path.stem}-questions")
            if not question_file_path.exists():
                logger.info("Generating questions and answers...")
                generate_questions(client, transcript, question_file_path)
            
            # Convert transcript to HTML
            transcript_md_path = audio_path.with_suffix('.md')
            if transcript_md_path.exists():
                transcript_html = convert_markdown_to_html(transcript_md_path)
                episode['fields']['episode-transcript'] = transcript_html
                
                # Generate excerpt
                excerpt = generate_episode_excerpt(transcript, config)
                episode['fields']['episode-description-excerpt'] = excerpt
            
            # Convert questions to HTML
            if question_file_path.exists():
                with open(question_file_path, 'r', encoding='utf-8') as f:
                    questions_md = f.read()
                
                qa_pairs = questions_md.strip().split('\n\n')
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
                
                questions_html = (
                    '<div class="qa-container">'
                    f'{" ".join(html_items)}'
                    '</div>'
                )
                episode['fields']['jessie-s-questions'] = questions_html
            
            # Clean up audio file
            audio_path.unlink()
            
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            # Continue with episode creation even if audio fails
        
        # Get categories and classify
        try:
            categories = get_categories(config)
            category = classify_episode_category(
                episode['fields']['name'],
                categories, 
                config
            )
            category_id = get_category_id(category, config)
            episode['fields']['episode-category'] = category_id
            logger.info(f"Episode classified as: {category}")
        except Exception as e:
            logger.error(f"Category classification failed: {e}")
            # Continue without category
        
        # Create episode in Webflow
        created_item = create_episode_in_webflow(episode, config)
        logger.info(f"Successfully created episode {episode_number} with ID: {created_item.get('_id')}")
        
        # Publish the site
        publish_site(config)
        logger.info("Published changes to live site")
        
    except Exception as e:
        logger.error(f"Failed to process missing episode {episode_number}: {e}")
        raise

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Process podcast episodes - fill gaps or add transcripts')
    parser.add_argument(
        '-n', '--num-episodes',
        type=int,
        default=1,
        help='Number of episodes to process (default: 1)'
    )
    parser.add_argument(
        '--fill-gaps',
        action='store_true',
        help='Fill missing episodes from RSS feed before processing episodes without transcripts'
    )
    return parser.parse_args()

def main():
    """Main function to process episodes - fill gaps or add transcripts"""
    try:
        args = parse_args()
        config = load_config()
        
        # Handle gap filling if requested
        if args.fill_gaps:
            logger.info("Gap filling mode enabled - checking for missing episodes...")
            
            # Get all episodes from RSS and Webflow
            rss_episodes = get_all_rss_episodes(config)
            webflow_episodes = get_all_webflow_episodes(config)
            
            # Find missing episodes
            missing_episodes = find_missing_episodes(rss_episodes, webflow_episodes)
            
            if missing_episodes:
                # Process up to num_episodes missing episodes
                num_to_process = min(args.num_episodes, len(missing_episodes))
                logger.info(f"Will process {num_to_process} missing episodes")
                
                # Get rate limit settings from config or use defaults
                rate_limit_delay = config.get('openai', {}).get('rate_limit_delay', 15)  # Default 15 seconds between requests
                rate_limit_retry_delay = config.get('openai', {}).get('rate_limit_retry_delay', 60)  # Default 60 seconds on rate limit
                
                for i in range(num_to_process):
                    missing_episode = missing_episodes[i]
                    retry_count = 0
                    max_retries = 3
                    
                    while retry_count < max_retries:
                        try:
                            process_missing_episode(missing_episode, config)
                            logger.info(f"Successfully created missing episode {missing_episode['number']}")
                            
                            # Add delay between episodes to avoid rate limiting
                            if i < num_to_process - 1:  # Don't delay after last episode
                                logger.info(f"Waiting {rate_limit_delay} seconds before next episode to avoid rate limits...")
                                time.sleep(rate_limit_delay)
                            break
                            
                        except Exception as e:
                            error_msg = str(e).lower()
                            if 'rate limit' in error_msg or '429' in error_msg or 'too many requests' in error_msg:
                                retry_count += 1
                                if retry_count < max_retries:
                                    wait_time = rate_limit_retry_delay * retry_count  # Exponential backoff
                                    logger.warning(f"Rate limit hit for episode {missing_episode['number']}. Waiting {wait_time} seconds before retry {retry_count}/{max_retries}...")
                                    time.sleep(wait_time)
                                    continue
                            
                            logger.error(f"Failed to create missing episode {missing_episode['number']}: {e}")
                            # Continue with next episode
                            break
                
                logger.info(f"Finished processing {num_to_process} missing episodes")
            else:
                logger.info("No missing episodes found")
        
        # Process episodes without transcripts (original functionality)
        logger.info("Getting episodes without transcripts...")
        episodes = get_episodes_without_transcript(config)
        
        if not episodes:
            logger.info("No episodes found without transcripts")
            return
            
        # Determine how many episodes to process
        remaining_quota = args.num_episodes
        if args.fill_gaps and 'missing_episodes' in locals() and missing_episodes:
            # Subtract the number of missing episodes we processed
            processed_missing = min(args.num_episodes, len(missing_episodes))
            remaining_quota = max(0, args.num_episodes - processed_missing)
            
        if remaining_quota > 0:
            num_to_process = min(remaining_quota, len(episodes))
            logger.info(f"Found {len(episodes)} episodes without transcripts, will process {num_to_process}")
            
            # Get rate limit settings from config or use defaults
            rate_limit_delay = config.get('openai', {}).get('rate_limit_delay', 15)  # Default 15 seconds between requests
            rate_limit_retry_delay = config.get('openai', {}).get('rate_limit_retry_delay', 60)  # Default 60 seconds on rate limit
            
            # Process the specified number of episodes
            for i in range(num_to_process):
                episode = episodes[i]
                episode_number = episode['fieldData'].get('episode-number')
                logger.info(f"Processing episode {episode_number} ({i + 1}/{num_to_process})...")
                
                retry_count = 0
                max_retries = 3
                
                while retry_count < max_retries:
                    try:
                        process_episode(episode, config)
                        logger.info(f"Successfully processed episode {episode_number}")
                        
                        # Add delay between episodes to avoid rate limiting
                        if i < num_to_process - 1:  # Don't delay after last episode
                            logger.info(f"Waiting {rate_limit_delay} seconds before next episode to avoid rate limits...")
                            time.sleep(rate_limit_delay)
                        break
                        
                    except Exception as e:
                        error_msg = str(e).lower()
                        if 'rate limit' in error_msg or '429' in error_msg or 'too many requests' in error_msg:
                            retry_count += 1
                            if retry_count < max_retries:
                                wait_time = rate_limit_retry_delay * retry_count  # Exponential backoff
                                logger.warning(f"Rate limit hit for episode {episode_number}. Waiting {wait_time} seconds before retry {retry_count}/{max_retries}...")
                                time.sleep(wait_time)
                                continue
                        
                        logger.error(f"Failed to process episode {episode_number}: {e}")
                        # Continue with next episode instead of exiting
                        break
            
            logger.info(f"Finished processing {num_to_process} episodes")
        else:
            logger.info("Episode quota exhausted by gap filling")
        
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 