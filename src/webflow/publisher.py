from utils.log_setup import setup_project_logging
logger = setup_project_logging()

import json
from typing import Dict
from requests.exceptions import RequestException
import requests

class WebflowPublishError(Exception):
    """Custom exception for Webflow publishing errors"""
    pass

def publish_site(config: dict) -> None:
    """
    Publish the Webflow site using deployments endpoint
    Args:
        config: Application configuration containing Webflow settings
    """
    url = f'https://api.webflow.com/v2/sites/{config["webflow"]["site_id"]}/deployments'
    
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'authorization': f'Bearer {config["webflow"]["api_token"]}',
    }
    
    try:
        # Create a deployment
        logger.info("Creating site deployment...")
        
        data = {
            "status": "staged"  # First stage the changes
        }
        
        # Create deployment
        deploy_response = requests.post(url, headers=headers, json=data)
        deploy_response.raise_for_status()
        deployment = deploy_response.json()
        deployment_id = deployment.get('id')
        
        if not deployment_id:
            raise WebflowPublishError("No deployment ID returned")
            
        # Publish the deployment
        publish_url = f'{url}/{deployment_id}/publish'
        logger.info(f"Publishing deployment {deployment_id}...")
        
        publish_response = requests.post(publish_url, headers=headers)
        publish_response.raise_for_status()
        
        logger.info("Site published successfully")
        
    except Exception as e:
        logger.error(f"Failed to publish site: {e}")
        if 'publish_response' in locals() and hasattr(publish_response, 'text'):
            logger.error(f"Publish Response: {publish_response.text}")
        if 'deploy_response' in locals() and hasattr(deploy_response, 'text'):
            logger.error(f"Deploy Response: {deploy_response.text}")
        raise WebflowPublishError(f"Failed to publish site: {str(e)}")

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

def publish_episode(episode_id: str, config: dict) -> None:
    """
    Publish a specific episode in Webflow CMS
    
    Args:
        episode_id: The ID of the episode to publish
        config: Application configuration containing Webflow settings
        
    Raises:
        WebflowPublishError: If there's an error publishing the episode
    """
    url = f'https://api.webflow.com/v2/sites/{config["webflow"]["site_id"]}/publish'
    
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'authorization': f'Bearer {config["webflow"]["api_token"]}',
    }
    
    try:
        # Prepare publish data according to API spec
        publish_data = {
            "publishToWebflowSubdomain": True  # Ensure changes are published to Webflow subdomain
        }
        
        # If custom domains are configured, include them
        if "custom_domains" in config["webflow"]:
            publish_data["customDomains"] = config["webflow"]["custom_domains"]
        
        logger.info("Publishing site changes...")
        publish_response = requests.post(url, headers=headers, json=publish_data)
        
        # Handle rate limit (1 publish per minute)
        if publish_response.status_code == 429:
            logger.warning("Hit rate limit when publishing. Please wait one minute before retrying.")
            raise WebflowPublishError("Publishing rate limit exceeded (1 publish per minute)")
            
        publish_response.raise_for_status()
        
        logger.info("Successfully published episode")
            
    except Exception as e:
        error_msg = f"Failed to publish episode (changes were still saved): {e}"
        if 'publish_response' in locals():
            logger.error(f"Response Status: {publish_response.status_code}")
            logger.error(f"Response Body: {publish_response.text}")
        logger.warning(error_msg)
        raise WebflowPublishError(error_msg) 