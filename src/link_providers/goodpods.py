from utils.log_setup import setup_project_logging
logger = setup_project_logging()

def get_goodpods_link(episode_number: int, episode_title: str) -> str:
    """
    Get the Goodpods link for the episode
    
    Args:
        episode_number: Episode number to find
        episode_title: Episode title to use in URL
    
    Returns:
        Goodpods episode URL
    """
    try:
        podcast_id = "274363"  # Fixed ID for Market MakeHer podcast
        
        # Generate the URL-friendly title part
        title_slug = generate_slug(episode_title)
        
        # Construct the full URL with episode number and title
        return f"https://goodpods.com/podcasts/market-makeher-podcast-{podcast_id}/{episode_number}-{title_slug}"
        
    except Exception as e:
        logger.error(f"Error generating Goodpods link: {e}")
        return None 