from typing import List, Dict, Optional
import requests
from utils.log_setup import setup_project_logging
logger = setup_project_logging()

class WebflowCategoryError(Exception):
    """Custom exception for category operations"""
    pass

def get_categories(config: dict) -> List[str]:
    """Get list of category names from Webflow collection"""
    try:
        url = f'https://api.webflow.com/v2/collections/{config["webflow"]["category_collection_id"]}/items'
        
        headers = {
            'accept': 'application/json',
            'authorization': f'Bearer {config["webflow"]["api_token"]}',
            'accept-version': '2.0.0'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Extract category names
        categories = [
            item['fieldData']['name'] 
            for item in response.json().get('items', [])
            if 'name' in item.get('fieldData', {})
        ]
        
        if not categories:
            raise ValueError("No categories found in collection")
            
        return categories
        
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise

def find_category_id(categories: List[Dict], category_name: str) -> Optional[str]:
    """Find category ID by name"""
    for category in categories:
        if category['name'].lower() == category_name.lower():
            return category['id']
    return None 