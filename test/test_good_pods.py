#!/usr/bin/env python3
import requests
import yaml
import logging
import sys
from bs4 import BeautifulSoup
import json
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
        # Create debug directory in project root
        debug_dir = ROOT_DIR / 'debug'
        debug_dir.mkdir(exist_ok=True)
        
        # Fetch the page content
        logger.info("Fetching Goodpods page content...")
        html_content = get_goodpods_page()
        
        # Save the raw HTML to a file for inspection
        html_path = debug_dir / 'goodpods_page.html'
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"Raw HTML saved to {html_path}")
        
        # Parse with BeautifulSoup for initial inspection
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Save JSON-LD data analysis
        json_ld_path = debug_dir / 'goodpods_jsonld.txt'
        with open(json_ld_path, 'w', encoding='utf-8') as f:
            # Look at all script tags with type application/ld+json
            f.write("JSON-LD Data Analysis:\n")
            scripts = soup.find_all('script', {'type': 'application/ld+json'})
            for i, script in enumerate(scripts):
                try:
                    data = json.loads(script.string)
                    f.write(f"\nScript {i + 1}:\n")
                    f.write(f"Type: {data.get('@type')}\n")
                    if isinstance(data, dict) and 'itemListElement' in data:
                        f.write("Found itemListElement!\n")
                        for item in data['itemListElement']:
                            if 'item' in item and 'url' in item['item']:
                                f.write(f"URL: {item['item']['url']}\n")
                except json.JSONDecodeError:
                    f.write(f"Could not parse script {i + 1}\n")
                f.write("-" * 50 + "\n")
        
        logger.info(f"JSON-LD analysis saved to {json_ld_path}")

        # Save link analysis
        links_path = debug_dir / 'goodpods_links.txt'
        with open(links_path, 'w', encoding='utf-8') as f:
            f.write("Regular Links Analysis:\n")
            all_links = soup.find_all('a', href=lambda h: h and '/podcasts/market-makeher-podcast-274363/' in h)
            for link in all_links:
                f.write(f"Link text: {link.text.strip()}\n")
                f.write(f"Link href: {link['href']}\n")
                f.write("-" * 50 + "\n")
        
        logger.info(f"Links analysis saved to {links_path}")
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    main() 