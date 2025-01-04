from googleapiclient.discovery import build
from utils.config import load_config
from utils.log_setup import setup_project_logging
import json
from pathlib import Path
import re
import argparse

logger = setup_project_logging()

class YouTubeEpisodeError(Exception):
    """Custom exception for YouTube episode fetching failures"""
    pass

def fetch_all_channel_videos(save_to_debug=True):
    """
    Fetch all videos from the configured YouTube channel, handling pagination.
    
    Args:
        save_to_debug: If True, saves the results to debug/youtube_channel_videos.json
        
    Returns:
        dict: Complete response with all video items
        
    Raises:
        YouTubeEpisodeError: If there's an error fetching the videos
    """
    config = load_config()
    
    if 'youtube' not in config:
        raise YouTubeEpisodeError("YouTube configuration not found in config.yaml")
        
    try:
        youtube = build('youtube', 'v3', developerKey=config['youtube']['api_key'])
        all_items = []
        next_page_token = None
        
        while True:
            request = youtube.search().list(
                part="id,snippet",
                channelId=config['youtube']['channel_id'],
                maxResults=50,
                order="date",
                type="video",
                pageToken=next_page_token
            )
            
            response = request.execute()
            all_items.extend(response.get('items', []))
            logger.info(f"Fetched {len(all_items)} videos so far...")
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        
        # Construct the final response
        result = {
            "kind": "youtube#searchListResponse",
            "etag": response.get('etag'),
            "pageInfo": {
                "totalResults": len(all_items),
                "resultsPerPage": len(all_items)
            },
            "items": all_items
        }
        
        if save_to_debug:
            debug_dir = Path(__file__).parent.parent.parent / 'debug'
            debug_dir.mkdir(exist_ok=True)
            with open(debug_dir / 'youtube_channel_videos.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to fetch YouTube channel videos: {e}")
        raise YouTubeEpisodeError(f"Failed to fetch YouTube channel videos: {e}")

def get_episode_url(episode_number: int) -> str:
    """
    Get the YouTube URL for a specific episode number.
    
    Args:
        episode_number: The episode number to search for
        
    Returns:
        str: The YouTube URL for the episode
        
    Raises:
        YouTubeEpisodeError: If episode cannot be found or there's an API error
    """
    config = load_config()
    
    if 'youtube' not in config:
        raise YouTubeEpisodeError("YouTube configuration not found in config.yaml")
        
    try:
        youtube = build('youtube', 'v3', developerKey=config['youtube']['api_key'])
        
        # Search for videos in the channel
        search_query = f"{config['youtube']['search_prefix']} {episode_number}"
        
        request = youtube.search().list(
            part="id,snippet",
            channelId=config['youtube']['channel_id'],
            q=search_query,
            type="video",
            maxResults=1
        )
        
        response = request.execute()
        
        if not response.get('items'):
            raise YouTubeEpisodeError(f"No episode found with number {episode_number}")
            
        video_id = response['items'][0]['id']['videoId']
        return f"https://www.youtube.com/watch?v={video_id}"
        
    except Exception as e:
        logger.error(f"Failed to fetch YouTube episode {episode_number}: {e}")
        raise YouTubeEpisodeError(f"Failed to fetch YouTube episode: {e}")

def get_episode_urls(episode_numbers: list[int]) -> dict[int, str]:
    """
    Get YouTube URLs for multiple episode numbers.
    
    Args:
        episode_numbers: List of episode numbers to fetch
        
    Returns:
        dict: Mapping of episode numbers to their YouTube URLs
        
    Raises:
        YouTubeEpisodeError: If there's an error fetching any episode
    """
    urls = {}
    for number in episode_numbers:
        try:
            urls[number] = get_episode_url(number)
        except YouTubeEpisodeError as e:
            logger.warning(f"Skipping episode {number}: {e}")
            continue
    return urls

def extract_episode_number(title: str) -> int | None:
    """
    Extract episode number from a video title if it exists.
    
    Args:
        title: Video title to parse
        
    Returns:
        int | None: Episode number if found, None otherwise
    """
    # Look for patterns like "Ep. 67" or "Episode 67"
    match = re.search(r'Ep(?:isode)?\.?\s*(\d+)', title)
    if match:
        return int(match.group(1))
    return None

def get_full_episodes(videos_data: dict) -> list[dict]:
    """
    Filter video data to only include full episodes with episode numbers.
    
    Args:
        videos_data: Complete YouTube API response with video items
        
    Returns:
        list: List of video items that are full episodes, sorted by episode number
    """
    full_episodes = []
    
    for item in videos_data.get('items', []):
        title = item.get('snippet', {}).get('title', '')
        episode_number = extract_episode_number(title)
        if episode_number is not None:
            item['episode_number'] = episode_number
            full_episodes.append(item)
    
    # Sort by episode number
    return sorted(full_episodes, key=lambda x: x['episode_number'], reverse=True) 

def main():
    parser = argparse.ArgumentParser(description='Fetch YouTube videos for Market MakeHer Podcast')
    parser.add_argument('--debug', action='store_true', help='Save results to debug/youtube_channel_videos.json')
    args = parser.parse_args()
    
    try:
        videos = fetch_all_channel_videos(save_to_debug=args.debug)
        full_episodes = get_full_episodes(videos)
        logger.info(f"Found {len(full_episodes)} full episodes")
        
        if not args.debug:
            # Print results to console if not saving to debug
            for episode in full_episodes:
                print(f"Episode {episode['episode_number']}: {episode['snippet']['title']}")
                print(f"URL: https://www.youtube.com/watch?v={episode['id']['videoId']}")
                print("---")
    
    except YouTubeEpisodeError as e:
        logger.error(str(e))
        exit(1)

if __name__ == '__main__':
    main() 