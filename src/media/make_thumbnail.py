import os
import sys
import argparse
import logging
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def create_thumbnail(
    text: str,
    input_image_path: str,
    output_name: Optional[str] = None,
    font_size: int = 75,
    font_color: str = "#FFFFFF",
    font_path: Optional[str] = None,
    position: Optional[tuple] = None,
    alignment: str = "center"
) -> str:
    """
    Creates a thumbnail by adding text to an existing image if it doesn't already exist
    
    Args:
        text: The text to add to the thumbnail
        input_image_path: Path to the base image
        output_name: Optional name for the output file (without extension)
        font_size: Size of the font (default: 75)
        font_color: Color of the text (default: white)
        font_path: Path to a custom font file (TTF/OTF)
        position: Optional tuple of coordinates for custom position
        alignment: Alignment of the text (default: center)
        
    Returns:
        Path to the thumbnail (either existing or newly created)
    """
    try:
        # Update output directory to use the root debug directory
        output_dir = Path(__file__).parent.parent.parent / 'debug' / 'images' / 'thumbnails'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename
        if output_name is None:
            base_name = os.path.splitext(os.path.basename(input_image_path))[0]
            output_name = f"thumbnail_{base_name}"
            
        output_path = output_dir / f"{output_name}.png"
        
        # Check if thumbnail already exists
        if os.path.exists(output_path):
            logging.info(f"Thumbnail already exists at: {output_path}")
            return output_path
            
        # If thumbnail doesn't exist, create it
        logging.info(f"Creating new thumbnail at: {output_path}")
        
        # Open and create a copy of the image
        with Image.open(input_image_path) as img:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Create a copy to work with
            thumbnail = img.copy()
            draw = ImageDraw.Draw(thumbnail)
            
            # Updated font loading logic
            try:
                if font_path:
                    font = ImageFont.truetype(font_path, font_size)
                    logging.info(f"Loaded custom font: {font_path} with size {font_size}")
                else:
                    # Try Arial first, then system default
                    try:
                        font = ImageFont.truetype("arial.ttf", font_size)
                        logging.info(f"Loaded Arial font with size {font_size}")
                    except OSError:
                        font = ImageFont.load_default()
                        logging.warning("Arial font not found, using default font")
            except OSError as e:
                logging.warning(f"Failed to load custom font: {str(e)}, using default font")
                font = ImageFont.load_default()
            
            # Get image dimensions
            img_width, img_height = thumbnail.size
            
            # Get text size
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Calculate position based on alignment or use custom position
            if position:
                x, y = position
            else:
                if alignment == "center":
                    x = (img_width - text_width) // 2
                    y = img_height // 3 - text_height // 2
                elif alignment == "top-left":
                    x, y = 0, 0
                elif alignment == "bottom-right":
                    x = img_width - text_width
                    y = img_height - text_height
                # Add more alignment options as needed
            
            # Add text to image
            draw.text(
                (x, y),
                text,
                font=font,
                fill=font_color
            )
            
            # Save the thumbnail
            thumbnail.save(output_path, "PNG")
            
            logging.info(f"New thumbnail created successfully at: {output_path}")
            return output_path
            
    except Exception as e:
        logging.error(f"Failed to create thumbnail: {str(e)}")
        raise

def main():
    # Update argument parser
    parser = argparse.ArgumentParser(description='Create a thumbnail with custom text')
    parser.add_argument('text', help='Text to add to the thumbnail')
    parser.add_argument('image', help='Path to the input image')
    parser.add_argument('--output', '-o', help='Output filename (without extension)', default=None)
    parser.add_argument('--font-size', '-s', type=int, default=75, help='Font size (default: 75)')
    parser.add_argument('--font-color', '-c', default="#FFFFFF", help='Font color (default: white)')
    parser.add_argument('--font-path', '-f', help='Path to custom font file (TTF/OTF)', default=None)
    
    args = parser.parse_args()
    
    try:
        output_path = create_thumbnail(
            text=args.text,
            input_image_path=args.image,
            output_name=args.output,
            font_size=args.font_size,
            font_color=args.font_color,
            font_path=args.font_path
        )
        print(f"Thumbnail path: {output_path}")
        
    except Exception as e:
        logging.error(f"Error creating thumbnail: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 