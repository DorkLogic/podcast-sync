#!/usr/bin/env python3
import sys
from pathlib import Path

# Add src directory to Python path
SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent
ROOT_DIR = SRC_DIR.parent
sys.path.append(str(SRC_DIR))

from media.make_thumbnail import create_thumbnail
from utils.optimize_image import optimize_image
from utils.log_setup import setup_project_logging

logger = setup_project_logging()

def parse_range(range_str: str) -> list[int]:
    """Parse a range string like '1-65' into a list of numbers"""
    try:
        start, end = map(int, range_str.split('-'))
        return list(range(start, end + 1))
    except ValueError:
        logger.error(f"Invalid range format: {range_str}. Expected format: 'start-end' (e.g., '1-65')")
        sys.exit(1)

def generate_thumbnails(episode_range: str, output_dir: str):
    """Generate thumbnails for a range of episode numbers"""
    try:
        # Convert output_dir to Path and make it absolute
        output_dir = Path(output_dir).resolve()
        logger.info(f"Output directory: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get episode numbers
        episodes = parse_range(episode_range)
        logger.info(f"Generating thumbnails for episodes {episodes[0]} to {episodes[-1]}")
        
        # Get paths for assets
        background_path = ROOT_DIR / "assets" / "images" / "default_episode_background.png"
        font_path = ROOT_DIR / "assets" / "fonts" / "AbrilFatface-Regular.ttf"

        logger.info(f"Root directory: {ROOT_DIR}")
        logger.info(f"Looking for background image at: {background_path}")
        logger.info(f"Looking for font file at: {font_path}")

        if not background_path.exists():
            logger.error(f"Background image not found at {background_path}")
            sys.exit(1)

        if not font_path.exists():
            logger.error(f"Font file not found at {font_path}")
            sys.exit(1)

        # Create temporary directory for large thumbnails
        temp_dir = output_dir / "temp"
        temp_dir.mkdir(exist_ok=True)

        # Generate thumbnails for each episode
        for episode_num in episodes:
            try:
                logger.info(f"Processing episode {episode_num}...")
                
                # Create large thumbnail first
                large_thumbnail_path = create_thumbnail(
                    text=str(episode_num),
                    input_image_path=str(background_path),
                    output_name=f"ep-{episode_num}_large",
                    font_size=225,
                    font_color="#FFFFFF",
                    font_path=str(font_path),
                    position=(420, 720)
                )
                
                if not Path(large_thumbnail_path).exists():
                    logger.error(f"Failed to create large thumbnail for episode {episode_num}")
                    continue

                logger.info(f"Created large thumbnail: {large_thumbnail_path}")

                # Optimize and save as final version - now using WEBP format
                output_path = output_dir / f"ep-{episode_num}.webp"  # Changed extension to .webp
                optimized_path = optimize_image(
                    input_path=large_thumbnail_path,
                    output_path=output_path,
                    max_size=(540, 540),
                    quality=85,
                    format='WEBP'  # Changed format to WEBP
                )

                if optimized_path:
                    logger.info(f"Created optimized thumbnail: {output_path}")
                    # Remove large version
                    Path(large_thumbnail_path).unlink()
                else:
                    logger.error(f"Failed to optimize thumbnail for episode {episode_num}")

            except Exception as e:
                logger.error(f"Failed to generate thumbnail for episode {episode_num}: {e}")
                continue

        # Clean up temporary directory
        if temp_dir.exists():
            temp_dir.rmdir()

    except Exception as e:
        logger.error(f"Error generating thumbnails: {e}")
        raise

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate_many_thumbs.py <episode-range> <output-directory>")
        print("Example: python generate_many_thumbs.py 1-65 /path/to/output/dir")
        sys.exit(1)

    episode_range = sys.argv[1]
    output_dir = sys.argv[2]
    
    try:
        generate_thumbnails(episode_range, output_dir)
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1) 