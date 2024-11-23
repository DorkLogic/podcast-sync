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

def main():
    """Get items and schemas from both collections"""
    config = load_config()
    
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