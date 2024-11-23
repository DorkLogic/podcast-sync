import logging
import json
from typing import Dict
from requests.exceptions import RequestException
import requests

logger = logging.getLogger(__name__)

class WebflowPublishError(Exception):
    """Custom exception for Webflow publishing errors"""
    pass

def publish_to_webflow(episode: dict, config: dict) -> dict:
    """
    Create and publish episode in Webflow collection
    Args:
        episode: Episode data to publish
        config: Application configuration
    Returns:
        Created item data from Webflow
    """
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
            
        # Valid fields from collection schema
        valid_fields = [
            'name',  # Episode Title
            'slug',  # Episode Link
            'episode-number',  # Episode - Number
            'episode-description-excerpt',  # Episode - Excerpt
            'description',  # Description
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
            "fieldData": episode['fields']
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
        raise WebflowPublishError(f"Webflow API error: {str(e)}") 