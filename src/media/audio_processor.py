import logging
from pathlib import Path
import subprocess
import os
import sys

logger = logging.getLogger(__name__)

def compress_audio(input_path: Path, max_size_mb: int = 25) -> Path:
    """
    Compress audio file to be under max_size_mb using FFmpeg directly
    Returns path to compressed file
    
    Args:
        input_path: Path to input audio file
        max_size_mb: Maximum size in MB for output file
        
    Returns:
        Path to compressed audio file
    """
    output_path = input_path.parent / f"compressed_{input_path.name}"
    
    try:
        # Get file size in MB
        file_size = input_path.stat().st_size / (1024 * 1024)
        
        if file_size <= max_size_mb:
            logger.info(f"File already under {max_size_mb}MB, skipping compression")
            return input_path
            
        logger.info(f"Compressing audio file from {file_size:.2f}MB to target {max_size_mb}MB")
        
        # Calculate target bitrate (kbps) with a safety margin
        # Get audio duration using ffprobe
        duration_cmd = [
            'ffprobe', 
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(input_path)
        ]
        
        duration = float(subprocess.check_output(duration_cmd).decode().strip())
        target_size_bytes = max_size_mb * 1024 * 1024 * 0.95  # 5% safety margin
        target_bitrate = int((target_size_bytes * 8) / duration / 1000)
        
        logger.info(f"Compressing with target bitrate: {target_bitrate}kbps")
        
        # Use FFmpeg for compression with the calculated bitrate
        compress_cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file if exists
            '-i', str(input_path),
            '-b:a', f'{target_bitrate}k',
            '-acodec', 'libmp3lame',
            str(output_path)
        ]
        
        subprocess.run(compress_cmd, check=True, capture_output=True)
        
        # Verify the output size
        new_size = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Successfully compressed file to {new_size:.2f}MB")
        
        if new_size > max_size_mb:
            raise Exception(f"Failed to compress file below {max_size_mb}MB (got {new_size:.2f}MB)")
        
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to compress audio: {e}")
        # Clean up failed output file if it exists
        if output_path.exists():
            try:
                os.unlink(output_path)
            except:
                pass
        raise

if __name__ == "__main__":
    # Configure logging for direct script execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python audio_processor.py <input_file> [max_size_mb]")
        print("Example: python audio_processor.py podcast.mp3 25")
        sys.exit(1)
        
    input_file = Path(sys.argv[1])
    max_size = float(sys.argv[2]) if len(sys.argv) > 2 else 25
    
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
        
    try:
        # Test FFmpeg availability
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
        
        # Compress the file
        output_path = compress_audio(input_file, max_size)
        print(f"\nSuccess! Compressed file saved to: {output_path}")
        
    except subprocess.CalledProcessError:
        print("Error: FFmpeg/FFprobe not found. Please install FFmpeg and make sure it's in your PATH")
        print("Windows: winget install -e --id Gyan.FFmpeg")
        print("macOS: brew install ffmpeg")
        print("Linux: sudo apt-get install ffmpeg")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1) 