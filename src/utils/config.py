import yaml
import sys
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

class ConfigError(Exception):
    """Custom exception for configuration errors"""
    pass

def load_config(config_path: str = 'config.yaml') -> Dict:
    """
    Load configuration from yaml file
    
    Args:
        config_path: Path to config file, defaults to 'config.yaml'
    
    Returns:
        Dict containing configuration
    
    Raises:
        ConfigError: If config file cannot be loaded or is invalid
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Validate required config sections
        required_sections = ['rss', 'webflow', 'spotify', 'apple_podcast']
        missing_sections = [section for section in required_sections if section not in config]
        
        if missing_sections:
            raise ConfigError(f"Missing required config sections: {', '.join(missing_sections)}")
            
        # Validate required fields in each section
        validate_config_section(config['webflow'], ['api_token', 'episode_collection_id'], 'webflow')
        validate_config_section(config['spotify'], ['client_id', 'client_secret', 'show_id'], 'spotify')
        validate_config_section(config['rss'], ['feed_url'], 'rss')
        validate_config_section(config['apple_podcast'], ['base_url'], 'apple_podcast')
        
        return config
        
    except yaml.YAMLError as e:
        raise ConfigError(f"Error parsing config file: {e}")
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {config_path}")
    except Exception as e:
        raise ConfigError(f"Error loading config: {e}")

def validate_config_section(section: Dict, required_fields: list, section_name: str):
    """
    Validate that a config section contains all required fields
    
    Args:
        section: Config section to validate
        required_fields: List of required field names
        section_name: Name of section for error messages
    
    Raises:
        ConfigError: If any required fields are missing
    """
    missing_fields = [field for field in required_fields if field not in section]
    if missing_fields:
        raise ConfigError(
            f"Missing required fields in {section_name} section: {', '.join(missing_fields)}"
        )

def create_example_config():
    """Create example config file if it doesn't exist"""
    example_config = {
        'rss': {
            'feed_url': 'https://example.com/feed.xml'
        },
        'webflow': {
            'api_token': 'your-webflow-api-token',
            'episode_collection_id': 'your-collection-id'
        },
        'spotify': {
            'client_id': 'your-spotify-client-id',
            'client_secret': 'your-spotify-client-secret',
            'show_id': 'your-show-id'
        },
        'apple_podcast': {
            'base_url': 'https://podcasts.apple.com/us/podcast/your-podcast'
        },
        'default_episode_color': '#000000',
        'default_episode_image': {
            'fileId': 'default-file-id',
            'url': 'https://example.com/default-image.png',
            'alt': None
        }
    }
    
    example_path = Path('config.yaml.example')
    if not example_path.exists():
        with open(example_path, 'w') as f:
            yaml.dump(example_config, f, default_flow_style=False) 