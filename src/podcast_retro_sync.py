#!/usr/bin/env python3
import sys
import logging
import argparse
from pathlib import Path
import requests
import yaml
from openai import OpenAI
from media.download_episode import download_episode
from media.transcribe_podcast import transcribe_audio_file, generate_questions
from utils.convert_md_to_html import convert_markdown_to_html
import feedparser
from webflow.publisher import publish_site

# Setup paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
DEBUG_DIR = ROOT_DIR / 'debug'
AUDIO_DIR = DEBUG_DIR / 'audio'
ASSETS_DIR = ROOT_DIR / 'assets'
ASSETS_IMAGES_DIR = ASSETS_DIR / 'images'
ASSETS_FONTS_DIR = ASSETS_DIR / 'fonts'

# Ensure directories exist
DEBUG_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)

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

def compress_audio(input_path: Path, max_size_mb: int = 25) -> Path:
    """
    Compress audio file to be under max_size_mb using pure Python
    Returns path to compressed file
    """
    output_path = input_path.parent / f"compressed_{input_path.name}"
    
    try:
        # Get file size in MB
        file_size = input_path.stat().st_size / (1024 * 1024)
        
        if file_size <= max_size_mb:
            logger.info(f"File already under {max_size_mb}MB, skipping compression")
            return input_path
            
        logger.info(f"Compressing audio file from {file_size:.2f}MB to target {max_size_mb}MB")
        
        # Instead of compressing, we'll split the file
        chunk_size = max_size_mb * 1024 * 1024  # Convert MB to bytes
        
        # Read the first chunk of the file
        with open(input_path, 'rb') as f:
            audio_data = f.read(int(chunk_size))
            
        # Write the chunk to the new file
        with open(output_path, 'wb') as f:
            f.write(audio_data)
            
        new_size = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Created compressed file of size: {new_size:.2f}MB")
        
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to compress audio: {e}")
        raise

def process_episode(episode: dict, config: dict) -> None:
    """Process a single episode to add transcript and questions"""
    episode_number = episode['fieldData'].get('episode-number')
    episode_id = episode['id']
    
    try:
        # Get audio URL
        logger.info(f"Getting audio URL for episode {episode_number}...")
        audio_url = get_episode_audio_url(episode_number, config)
        
        # Stream file and take first ~23MB to ensure we're under the limit
        logger.info("Streaming audio file...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.buzzsprout.com/'
        }
        
        response = requests.get(audio_url, stream=True, headers=headers)
        response.raise_for_status()
        
        # Create the audio directory if it doesn't exist
        AUDIO_DIR.mkdir(exist_ok=True)
        
        # Save 23MB to be well under the 25MB limit
        chunk_size = 23 * 1024 * 1024  # 23MB in bytes
        audio_path = AUDIO_DIR / f"ep-{episode_number}.mp3"
        
        bytes_written = 0
        with open(audio_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):  # Smaller chunks for more precise control
                if bytes_written >= chunk_size:
                    break
                if chunk:
                    current_chunk_size = len(chunk)
                    # Don't write if it would exceed our limit
                    if bytes_written + current_chunk_size > chunk_size:
                        remaining = chunk_size - bytes_written
                        f.write(chunk[:remaining])
                        bytes_written += remaining
                        break
                    f.write(chunk)
                    bytes_written += current_chunk_size
        
        actual_size = audio_path.stat().st_size / (1024 * 1024)
        logger.info(f"Saved first {actual_size:.2f}MB to {audio_path}")
        
        if actual_size >= 25:
            raise Exception(f"File size {actual_size:.2f}MB exceeds OpenAI's 25MB limit")
        
        # Transcribe the truncated audio file
        logger.info("Transcribing audio...")
        client = OpenAI(api_key=config['openai']['api_key'])
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

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Process podcast episodes without transcripts')
    parser.add_argument(
        '-n', '--num-episodes',
        type=int,
        default=1,
        help='Number of episodes to process (default: 1)'
    )
    return parser.parse_args()

def main():
    """Main function to process episodes without transcripts"""
    try:
        args = parse_args()
        config = load_config()
        
        # Get episodes without transcripts
        logger.info("Getting episodes without transcripts...")
        episodes = get_episodes_without_transcript(config)
        
        if not episodes:
            logger.info("No episodes found without transcripts")
            return
            
        # Determine how many episodes to process
        num_to_process = min(args.num_episodes, len(episodes))
        logger.info(f"Found {len(episodes)} episodes without transcripts, will process {num_to_process}")
        
        # Process the specified number of episodes
        for i in range(num_to_process):
            episode = episodes[i]
            episode_number = episode['fieldData'].get('episode-number')
            logger.info(f"Processing episode {episode_number} ({i + 1}/{num_to_process})...")
            try:
                process_episode(episode, config)
                logger.info(f"Successfully processed episode {episode_number}")
            except Exception as e:
                logger.error(f"Failed to process episode {episode_number}: {e}")
                # Continue with next episode instead of exiting
                continue
        
        logger.info(f"Finished processing {num_to_process} episodes")
        
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 