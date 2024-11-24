#!/usr/bin/env python3
import requests
import json
import yaml
import logging
import sys
import os
from pathlib import Path

# Define directory paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent

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
        config_path = ROOT_DIR / 'config.yaml'
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise

def get_collection_schema(collection_id: str, output_filename: str):
    """Get the schema for a Webflow collection"""
    config = load_config()
    
    headers = {
        'accept': 'application/json',
        'authorization': f'Bearer {config["webflow"]["api_token"]}',
        'accept-version': '2.0.0'
    }
    
    url = f'https://api.webflow.com/v2/collections/{collection_id}'
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Save response to file
        output_path = ROOT_DIR / 'debug' / output_filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(response.json(), f, indent=2)
            
        logger.info(f"Collection schema saved to {output_path}")
        
    except Exception as e:
        logger.error(f"Error getting collection schema: {e}")
        if hasattr(response, 'text'):
            logger.error(f"Response: {response.text}")
        raise

def get_collection_items(collection_id: str, output_filename: str):
    """Get items from a Webflow collection"""
    config = load_config()
    
    headers = {
        'accept': 'application/json',
        'authorization': f'Bearer {config["webflow"]["api_token"]}',
        'accept-version': '2.0.0',
        'Content-Type': 'application/json'
    }
    
    url = f'https://api.webflow.com/v2/collections/{collection_id}/items'
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Save response to file
        output_path = ROOT_DIR / 'debug' / output_filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(response.json(), f, indent=2)
            
        logger.info(f"Collection data saved to {output_path}")
        
    except Exception as e:
        logger.error(f"Error getting collection items: {e}")
        if hasattr(response, 'text'):
            logger.error(f"Response: {response.text}")
        raise

def get_sites(config: dict) -> None:
    """
    Fetch and display all available Webflow sites
    """
    try:
        url = 'https://api.webflow.com/v2/sites'
        
        headers = {
            'accept': 'application/json',
            'authorization': f'Bearer {config["webflow"]["api_token"]}'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 403 and 'missing_scopes' in response.text:
            logger.error("""
Your API token is missing required scopes. Please create a new API token with these scopes:
- sites:read

To create a new token:
1. Go to Webflow Dashboard > Account Settings > Workspace Settings > API Access
2. Create New Access Token
3. Enable the 'sites:read' scope
4. Copy the new token to your config.yaml
            """)
            return
            
        response.raise_for_status()
        
        sites = response.json()
        
        # Save full response to debug folder
        debug_dir = Path(__file__).parent.parent / 'debug'
        debug_dir.mkdir(exist_ok=True)
        
        # Save full response to file
        sites_file = debug_dir / 'webflow_sites.json'
        with open(sites_file, 'w', encoding='utf-8') as f:
            json.dump(sites, f, indent=2)
            
        # Print simplified site information
        print("\nAvailable Webflow Sites:")
        print("-" * 50)
        for site in sites.get('sites', []):
            print(f"Name: {site.get('displayName')}")
            print(f"ID: {site.get('id')}")
            print(f"Short Name: {site.get('shortName')}")
            print(f"Last Published: {site.get('lastPublished')}")
            if site.get('customDomains'):
                print("Custom Domains:")
                for domain in site['customDomains']:
                    print(f"  - {domain.get('url')}")
            print("-" * 50)
            
        logger.info(f"Full site details saved to {sites_file}")
        
    except Exception as e:
        logger.error(f"Failed to fetch Webflow sites: {e}")
        if 'response' in locals():
            logger.error(f"Response: {response.text}")
        raise

def main():
    """Get sites and collection information"""
    config = load_config()
    
    # Get sites first
    logger.info("Fetching Webflow sites...")
    try:
        get_sites(config)
    except Exception as e:
        logger.error("Failed to get sites, continuing with other operations...")
    
    # Get episodes collection schema and items
    logger.info("Fetching episodes collection schema...")
    get_collection_schema(
        config["webflow"]["episode_collection_id"],
        'webflow_episodes_schema.json'
    )
    
    logger.info("Fetching episodes collection items...")
    get_collection_items(
        config["webflow"]["episode_collection_id"],
        'webflow_episodes.json'
    )
    
    # Get categories collection schema and items
    logger.info("Fetching categories collection schema...")
    get_collection_schema(
        config["webflow"]["category_collection_id"],
        'webflow_categories_schema.json'
    )
    
    logger.info("Fetching categories collection items...")
    get_collection_items(
        config["webflow"]["category_collection_id"],
        'webflow_categories.json'
    )

if __name__ == "__main__":
    main() 