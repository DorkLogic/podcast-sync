import sys
import logging
from PIL import Image
import os
from pathlib import Path
import argparse
import time

logging.getLogger('PIL').addHandler(logging.NullHandler())


def cli_print(msg: str):
    """Simple print function for command line output"""
    print(msg)


def optimize_image(
    input_path: str | Path,
    output_path: str | Path = None,
    max_size: tuple[int, int] = (1200, 1200),
    quality: int = 85,
    format: str = 'WEBP',
    suffix: str = '_optimized'
) -> Path:
    """
    Optimize an image for web use by:
    1. Resizing to max dimensions while maintaining aspect ratio
    2. Converting to RGB mode if needed
    3. Optimizing quality/compression
    4. Using WebP or another web-friendly format
    """
    try:
        # Convert paths to Path objects
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input image not found: {input_path}")
        
        if output_path is None:
            # Use provided suffix for the output filename
            output_path = input_path.parent / f"{input_path.stem}{suffix}.{format.lower()}"
        else:
            output_path = Path(output_path)
        
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Open and process image
        with Image.open(input_path) as img:
            # Verify and reopen to avoid processing corrupt images
            img.verify()
            img = Image.open(input_path)

            # Convert to RGB if needed
            if img.mode in ('RGBA', 'P') and format == 'WEBP':
                img = img.convert('RGBA')  # WebP supports transparency
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Get current size
            current_width, current_height = img.size
            
            # Calculate new size maintaining aspect ratio
            ratio = min(max_size[0] / current_width, max_size[1] / current_height)
            
            if ratio < 1:  # Only resize if image is larger than max_size
                new_size = (int(current_width * ratio), int(current_height * ratio))
                cli_print(f"Resizing image from {img.size} to {new_size}")
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Save optimized image
            img.save(
                output_path,
                format=format,
                optimize=True,
                quality=quality
            )
            
            # Log optimization results
            original_size = os.path.getsize(input_path)
            optimized_size = os.path.getsize(output_path)
            reduction = (original_size - optimized_size) / original_size * 100
            
            cli_print(f"Image optimized: {input_path.name}")
            cli_print(f"Original size: {original_size / 1024:.1f}KB")
            cli_print(f"Optimized size: {optimized_size / 1024:.1f}KB")
            cli_print(f"Size reduction: {reduction:.1f}%")
            
            return output_path
    
    except (Image.UnidentifiedImageError, OSError) as e:
        cli_print(f"Skipping invalid or corrupted image: {input_path.name} ({e})")
        return None
    
    except Exception as e:
        cli_print(f"Failed to optimize image: {e}")
        raise


def optimize_images_in_directory(
    input_dir: str | Path,
    output_dir: str | Path = None,
    recursive: bool = False,
    max_size: tuple[int, int] = (1200, 1200),
    quality: int = 85,
    format: str = 'WEBP',
    suffix: str = '_optimized'
) -> list[Path]:
    """Optimize all images in a directory"""
    input_dir = Path(input_dir)
    if output_dir:
        output_dir = Path(output_dir)
    
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    
    # Get list of image files
    image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
    
    if recursive:
        image_files = [f for f in input_dir.rglob('*') if f.suffix.lower() in image_extensions]
    else:
        image_files = [f for f in input_dir.glob('*') if f.suffix.lower() in image_extensions]
    
    optimized_images = []
    start_time = time.time()
    
    for image_file in image_files:
        try:
            if output_dir:
                # Maintain directory structure in output_dir
                rel_path = image_file.relative_to(input_dir)
                output_path = output_dir / rel_path
            else:
                output_path = None
            
            optimized_path = optimize_image(
                input_path=image_file,
                output_path=output_path,
                max_size=max_size,
                quality=quality,
                format=format,
                suffix=suffix
            )
            
            if optimized_path:
                optimized_images.append(optimized_path)
        
        except Exception as e:
            cli_print(f"Failed to optimize {image_file.name}: {e}")
            continue
    
    cli_print(f"Processed {len(optimized_images)} images in {time.time() - start_time:.2f} seconds.")
    return optimized_images


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="""
        Optimize images for web use. This tool can:
        1. Resize images while maintaining aspect ratio
        2. Convert to web-friendly formats (WEBP, JPEG, PNG)
        3. Optimize quality and compression
        4. Process single images or entire directories
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "input_path",
        type=str,
        help="Path to input image or directory containing images"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output path. For single files: output filename. For directories: output directory"
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
        "-r", "--recursive",
        action="store_true",
        help="Process directories recursively"
    )
    
    parser.add_argument(
        "--suffix",
        type=str,
        default="_optimized",
        help="Suffix to add to optimized files when no output path is specified (default: _optimized)"
    )

    # Add examples to the epilog
    parser.epilog = """
Examples:
    # Optimize a single image to WEBP format
    python optimize_image.py input.jpg -o output.webp

    # Optimize a directory of images to WEBP format
    python optimize_image.py input_dir/ -o output_dir/

    # Optimize with custom settings
    python optimize_image.py input.jpg -o output.webp --max-width 800 --max-height 600 --quality 90

    # Process directory recursively with PNG output
    python optimize_image.py input_dir/ -o output_dir/ -r --format PNG

    # Use custom suffix for output files
    python optimize_image.py input.jpg --suffix _web

    # Use default output naming (adds _optimized suffix)
    python optimize_image.py input.jpg
    """
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    
    input_path = Path(args.input_path)
    output_path = Path(args.output) if args.output else None
    max_size = (args.max_width, args.max_height)
    
    try:
        if input_path.is_dir():
            optimize_images_in_directory(
                input_dir=input_path,
                output_dir=output_path,
                recursive=args.recursive,
                max_size=max_size,
                quality=args.quality,
                format=args.format,
                suffix=args.suffix
            )
        else:
            optimize_image(
                input_path=input_path,
                output_path=output_path,
                max_size=max_size,
                quality=args.quality,
                format=args.format,
                suffix=args.suffix
            )
    except Exception as e:
        cli_print(f"Error: {e}")
        sys.exit(1)
