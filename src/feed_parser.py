import feedparser
from utils.log_setup import setup_project_logging
from typing import Dict
from utils.text import generate_slug, get_episode_number, clean_html
from link_providers.apple import get_apple_podcast_link
from link_providers.spotify import get_spotify_podcast_link
from link_providers.goodpods import get_goodpods_link

logger = setup_project_logging()

class FeedParserError(Exception):
    """Custom exception for feed parsing errors"""
    pass

def get_latest_episode(config: Dict) -> Dict:
    """Fetch and parse the latest episode from RSS feed"""
    try:
        feed = feedparser.parse(config['rss']['feed_url'])
        
        if feed.bozo:
            raise FeedParserError(f"RSS feed parsing error: {feed.bozo_exception}")
        
        if not feed.entries:
            raise FeedParserError("No episodes found in feed")
        
        entry = feed.entries[0]  # Get latest episode
        episode_number = get_episode_number(entry.title)
        
        # Format title to use "Ep N:" format
        title_without_number = re.sub(r'^\d+\.\s*', '', entry.title)
        formatted_title = f"Ep {episode_number}: {title_without_number}" if episode_number else entry.title
        
        # Get platform links
        apple_podcast_link = get_apple_podcast_link(episode_number, config['apple_podcast']['base_url']) if episode_number else None
        spotify_link = get_spotify_podcast_link(episode_number, config) if episode_number else None
        
        # Map RSS feed data to Webflow collection fields
        episode = {
            'fields': {
                'name': formatted_title,
                'slug': generate_slug(entry.title),
                'episode-number': episode_number,
                'episode-description-excerpt': clean_html(entry.summary)[:73],
                'description': entry.content[0].value if entry.content else entry.summary,
                'episode-featured': True,
                'episode-color': config['default_episode_color'],
                'episode-main-image': config['default_episode_image']
            }
        }
        
        # Add platform links if found
        if apple_podcast_link:
            episode['fields']['apple-podcast-link-for-player'] = apple_podcast_link[0]
            episode['fields']['episode-apple-podcasts-link'] = apple_podcast_link[1]
        
        if spotify_link:
            episode['fields']['episode-spotify-link'] = spotify_link
            
        if episode_number:
            goodpods_link = get_goodpods_link(episode_number, entry.title)
            episode['fields']['episode-anchor-link'] = goodpods_link
        
        return episode
        
    except Exception as e:
        raise FeedParserError(f"Failed to parse RSS feed: {str(e)}") 