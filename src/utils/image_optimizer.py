import os
import sys
import time
import argparse
from pathlib import Path
from PIL import Image
import logging
from typing import List, Dict, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Suppress PIL debug logs
logging.getLogger('PIL').addHandler(logging.NullHandler())

class ImageOptimizer:
    """
    A class to optimize images in a directory and its subdirectories.
    """
    
    def __init__(
        self,
        max_size: Tuple[int, int] = (1200, 1200),
        quality: int = 85,
        format: str = 'WEBP',
        suffix: str = '_optimized',
        backup: bool = True,
        dry_run: bool = False
    ):
        """
        Initialize the ImageOptimizer.
        
        Args:
            max_size: Maximum dimensions (width, height) for resizing
            quality: Quality setting for compression (1-100)
            format: Output format ('WEBP', 'JPEG', 'PNG')
            suffix: Suffix to add to optimized files
            backup: Whether to create a backup of original files
            dry_run: If True, only show what would be done without making changes
        """
        self.max_size = max_size
        self.quality = quality
        self.format = format
        self.suffix = suffix
        self.backup = backup
        self.dry_run = dry_run
        self.image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff')
        self.stats = {
            'processed': 0,
            'skipped': 0,
            'failed': 0,
            'total_size_before': 0,
            'total_size_after': 0
        }
    
    def optimize_image(self, input_path: Path, output_path: Optional[Path] = None) -> Optional[Path]:
        """
        Optimize a single image.
        
        Args:
            input_path: Path to the input image
            output_path: Path to save the optimized image (optional)
            
        Returns:
            Path to the optimized image or None if optimization failed
        """
        try:
            if not input_path.exists():
                logger.error(f"Input image not found: {input_path}")
                self.stats['failed'] += 1
                return None
            
            if output_path is None:
                # Use provided suffix for the output filename
                output_path = input_path.parent / f"{input_path.stem}{self.suffix}.{self.format.lower()}"
            else:
                output_path = Path(output_path)
            
            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Skip if output file already exists and is newer than input
            if output_path.exists() and output_path.stat().st_mtime > input_path.stat().st_mtime:
                logger.info(f"Skipping {input_path.name} - optimized version already exists and is up to date")
                self.stats['skipped'] += 1
                return output_path
            
            # Create backup if requested
            if self.backup and not self.dry_run:
                backup_path = input_path.parent / f"{input_path.stem}_original{input_path.suffix}"
                if not backup_path.exists():
                    import shutil
                    shutil.copy2(input_path, backup_path)
                    logger.info(f"Created backup: {backup_path}")
            
            if self.dry_run:
                logger.info(f"Would optimize: {input_path} -> {output_path}")
                self.stats['processed'] += 1
                return output_path
            
            # Open and process image
            with Image.open(input_path) as img:
                # Verify and reopen to avoid processing corrupt images
                img.verify()
                img = Image.open(input_path)
                
                # Convert to RGB if needed
                if img.mode in ('RGBA', 'P') and self.format == 'WEBP':
                    img = img.convert('RGBA')  # WebP supports transparency
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Get current size
                current_width, current_height = img.size
                
                # Calculate new size maintaining aspect ratio
                ratio = min(self.max_size[0] / current_width, self.max_size[1] / current_height)
                
                if ratio < 1:  # Only resize if image is larger than max_size
                    new_size = (int(current_width * ratio), int(current_height * ratio))
                    logger.info(f"Resizing image from {img.size} to {new_size}")
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Save optimized image
                img.save(
                    output_path,
                    format=self.format,
                    optimize=True,
                    quality=self.quality
                )
                
                # Log optimization results
                original_size = os.path.getsize(input_path)
                optimized_size = os.path.getsize(output_path)
                reduction = (original_size - optimized_size) / original_size * 100
                
                logger.info(f"Image optimized: {input_path.name}")
                logger.info(f"Original size: {original_size / 1024:.1f}KB")
                logger.info(f"Optimized size: {optimized_size / 1024:.1f}KB")
                logger.info(f"Size reduction: {reduction:.1f}%")
                
                # Update stats
                self.stats['processed'] += 1
                self.stats['total_size_before'] += original_size
                self.stats['total_size_after'] += optimized_size
                
                return output_path
        
        except (Image.UnidentifiedImageError, OSError) as e:
            logger.error(f"Skipping invalid or corrupted image: {input_path.name} ({e})")
            self.stats['failed'] += 1
            return None
        
        except Exception as e:
            logger.error(f"Failed to optimize image: {e}")
            self.stats['failed'] += 1
            return None
    
    def process_directory(self, input_dir: Path, output_dir: Optional[Path] = None, recursive: bool = True) -> List[Path]:
        """
        Process all images in a directory.
        
        Args:
            input_dir: Directory containing images
            output_dir: Directory to save optimized images (optional)
            recursive: Whether to process subdirectories
            
        Returns:
            List of paths to optimized images
        """
        input_dir = Path(input_dir)
        if output_dir:
            output_dir = Path(output_dir)
        
        if not input_dir.exists():
            logger.error(f"Input directory not found: {input_dir}")
            return []
        
        # Get list of image files
        if recursive:
            image_files = [f for f in input_dir.rglob('*') if f.suffix.lower() in self.image_extensions]
        else:
            image_files = [f for f in input_dir.glob('*') if f.suffix.lower() in self.image_extensions]
        
        optimized_images = []
        start_time = time.time()
        
        logger.info(f"Found {len(image_files)} images to process")
        
        for image_file in image_files:
            try:
                if output_dir:
                    # Maintain directory structure in output_dir
                    rel_path = image_file.relative_to(input_dir)
                    output_path = output_dir / rel_path
                else:
                    output_path = None
                
                optimized_path = self.optimize_image(
                    input_path=image_file,
                    output_path=output_path
                )
                
                if optimized_path:
                    optimized_images.append(optimized_path)
            
            except Exception as e:
                logger.error(f"Failed to optimize {image_file.name}: {e}")
                self.stats['failed'] += 1
                continue
        
        elapsed_time = time.time() - start_time
        logger.info(f"Processed {len(optimized_images)} images in {elapsed_time:.2f} seconds")
        
        # Print summary
        total_reduction = 0
        if self.stats['total_size_before'] > 0:
            total_reduction = (self.stats['total_size_before'] - self.stats['total_size_after']) / self.stats['total_size_before'] * 100
        
        logger.info("Summary:")
        logger.info(f"  Processed: {self.stats['processed']} images")
        logger.info(f"  Skipped: {self.stats['skipped']} images")
        logger.info(f"  Failed: {self.stats['failed']} images")
        logger.info(f"  Total size before: {self.stats['total_size_before'] / (1024*1024):.2f}MB")
        logger.info(f"  Total size after: {self.stats['total_size_after'] / (1024*1024):.2f}MB")
        logger.info(f"  Total reduction: {total_reduction:.1f}%")
        
        return optimized_images


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="""
        Optimize images in a directory and its subdirectories.
        This tool can:
        1. Resize images while maintaining aspect ratio
        2. Convert to web-friendly formats (WEBP, JPEG, PNG)
        3. Optimize quality and compression
        4. Create backups of original files
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "input_dir",
        type=str,
        help="Directory containing images to optimize"
    )
    
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        help="Directory to save optimized images (optional)"
    )
    
    parser.add_argument(
        "--max-width",
        type=int,
        default=1200,
        help="Maximum width of output images (default: 1200)"
    )
    
    parser.add_argument(
        "--max-height",
        type=int,
        default=1200,
        help="Maximum height of output images (default: 1200)"
    )
    
    parser.add_argument(
        "--quality",
        type=int,
        default=85,
        choices=range(1, 101),
        metavar="[1-100]",
        help="Output image quality, 1-100 (default: 85)"
    )
    
    parser.add_argument(
        "--format",
        type=str,
        choices=["JPEG", "PNG", "WEBP"],
        default="WEBP",
        help="Output image format (default: WEBP)"
    )
    
    parser.add_argument(
        "--suffix",
        type=str,
        default="_optimized",
        help="Suffix to add to optimized files (default: _optimized)"
    )
    
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create backups of original files"
    )
    
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not process subdirectories"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    # Add examples to the epilog
    parser.epilog = """
Examples:
    # Optimize all images in a directory
    python image_optimizer.py /path/to/images
    
    # Optimize images with custom settings
    python image_optimizer.py /path/to/images -o /path/to/output --max-width 800 --quality 90
    
    # Process directory without recursion
    python image_optimizer.py /path/to/images --no-recursive
    
    # Show what would be done without making changes
    python image_optimizer.py /path/to/images --dry-run
    
    # Do not create backups of original files
    python image_optimizer.py /path/to/images --no-backup
    """
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir) if args.output_dir else None
    max_size = (args.max_width, args.max_height)
    
    try:
        optimizer = ImageOptimizer(
            max_size=max_size,
            quality=args.quality,
            format=args.format,
            suffix=args.suffix,
            backup=not args.no_backup,
            dry_run=args.dry_run
        )
        
        optimizer.process_directory(
            input_dir=input_dir,
            output_dir=output_dir,
            recursive=not args.no_recursive
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1) 