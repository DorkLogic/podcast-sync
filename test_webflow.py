#!/usr/bin/env python3
import requests
import json
import yaml
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from config.yaml"""
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise

def get_recent_episode():
    """Get most recent episode from Webflow collection"""
    config = load_config()
    
    headers = {
        'accept': 'application/json',
        'authorization': f'Bearer {config["webflow"]["api_token"]}',
        'accept-version': '2.0.0',
        'Content-Type': 'application/json'
    }
    
    # Get collection items
    url = f'https://api.webflow.com/v2/collections/{config["webflow"]["collection_id"]}/items'
    
    try:
        response = requests.get(
            url, 
            headers=headers
        )
        response.raise_for_status()
        
        # Save response to file
        with open('webflow_recent_ep.json', 'w', encoding='utf-8') as f:
            json.dump(response.json(), f, indent=2)
            
        logger.info("Recent episode data saved to webflow_recent_ep.json")
        
    except Exception as e:
        logger.error(f"Error getting recent episode: {e}")
        if hasattr(response, 'text'):
            logger.error(f"Response: {response.text}")
        raise

if __name__ == "__main__":
    get_recent_episode() 