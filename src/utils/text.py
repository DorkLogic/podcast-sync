import re
import html
from bs4 import BeautifulSoup
from utils.log_setup import setup_project_logging
logger = setup_project_logging()

def generate_slug(title: str) -> str:
    """Generate a URL-friendly slug from the episode title"""
    # Extract episode number if present
    episode_match = re.match(r'^(\d+)\.', title)
    episode_num = episode_match.group(1) if episode_match else ''
    
    # Remove episode number from start if present
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

def sanitize_filename(filename: str, replacement: str = '_') -> str:
    """
    Sanitize a filename by removing/replacing invalid characters.
    
    Args:
        filename: The filename to sanitize
        replacement: Character to replace invalid chars with (default: '_')
    
    Returns:
        Sanitized filename safe for use on all platforms
    """
    # Remove or replace invalid characters for Windows filenames
    # Invalid chars: < > : " / \ | ? * and control chars (0-31)
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    filename = re.sub(invalid_chars, replacement, filename)
    
    # Remove emoji and other non-ASCII characters that might cause issues
    # Keep only ASCII letters, numbers, spaces, hyphens, underscores, and dots
    filename = re.sub(r'[^\x20-\x7E]', replacement, filename)
    
    # Clean up multiple consecutive replacements
    if replacement:
        filename = re.sub(f'{re.escape(replacement)}+', replacement, filename)
    
    # Remove leading/trailing spaces and dots (Windows doesn't like these)
    filename = filename.strip(' .')
    
    # Ensure filename isn't empty after sanitization
    if not filename:
        filename = 'unnamed'
    
    # Limit length to be safe (255 chars is typical limit, but leave room for path)
    max_length = 200
    if len(filename) > max_length:
        # Keep file extension if present
        name_parts = filename.rsplit('.', 1)
        if len(name_parts) == 2:
            name, ext = name_parts
            filename = name[:max_length - len(ext) - 1] + '.' + ext
        else:
            filename = filename[:max_length]
    
    return filename 