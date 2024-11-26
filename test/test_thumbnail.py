#!/usr/bin/env python3
import sys
from pathlib import Path
import logging

# Define directory paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
DEBUG_DIR = ROOT_DIR / 'debug'

# Add src directory to Python path
src_dir = ROOT_DIR / 'src'
sys.path.append(str(src_dir))

from media.make_thumbnail import create_thumbnail

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def test_thumbnail_creation():
    """Test thumbnail creation with specific parameters"""
    try:
        # Setup paths using consistent directory structure
        assets_dir = ROOT_DIR / "assets"
        
        # Set paths for assets
        background_path = assets_dir / "images" / "default_episode_background.png"
        font_path = assets_dir / "fonts" / "AbrilFatface-Regular.ttf"

        # Create thumbnail - output will automatically go to debug/images/thumbnails
        # due to the logic in create_thumbnail function
        thumbnail_path = create_thumbnail(
            text="64",
            input_image_path=str(background_path),
            output_name='test_64',
            font_size=225,
            font_color="#FFFFFF",
            font_path=str(font_path),
            position=(420, 720)
        )
        
        logger.info(f"Test thumbnail created successfully at: {thumbnail_path}")
        
    except Exception as e:
        logger.error(f"Failed to create test thumbnail: {e}")
        raise

if __name__ == "__main__":
    test_thumbnail_creation() 