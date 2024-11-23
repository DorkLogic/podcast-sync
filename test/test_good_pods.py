#!/usr/bin/env python3
import requests
import yaml
import logging
import sys
from bs4 import BeautifulSoup
import json
import re
import os

# Configure logging to handle Unicode
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

def get_goodpods_page():
    """Fetch the Goodpods page content"""
    config = load_config()
    base_url = config['goodPods']['base_url']
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Error fetching Goodpods page: {e}")
        raise

def main():
    try:
        # Create debug directory if it doesn't exist
        os.makedirs('debug', exist_ok=True)
        
        # Fetch the page content
        logger.info("Fetching Goodpods page content...")
        html_content = get_goodpods_page()
        
        # Save the raw HTML to a file for inspection
        with open('debug/goodpods_page.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info("Raw HTML saved to debug/goodpods_page.html")
        
        # Parse with BeautifulSoup for initial inspection
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look at all script tags with type application/ld+json
        logger.info("\nExamining JSON-LD data:")
        scripts = soup.find_all('script', {'type': 'application/ld+json'})
        for i, script in enumerate(scripts):
            try:
                data = json.loads(script.string)
                logger.info(f"\nScript {i + 1}:")
                logger.info(f"Type: {data.get('@type')}")
                if isinstance(data, dict) and 'itemListElement' in data:
                    logger.info("Found itemListElement!")
                    for item in data['itemListElement']:
                        if 'item' in item and 'url' in item['item']:
                            logger.info(f"URL: {item['item']['url']}")
            except json.JSONDecodeError:
                logger.error(f"Could not parse script {i + 1}")
                continue

        # Also look for regular links
        logger.info("\nExamining regular links:")
        all_links = soup.find_all('a', href=lambda h: h and '/podcasts/market-makeher-podcast-274363/' in h)
        for link in all_links:
            logger.info(f"Link text: {link.text.strip()}")
            logger.info(f"Link href: {link['href']}")
            logger.info("---")
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    main() 