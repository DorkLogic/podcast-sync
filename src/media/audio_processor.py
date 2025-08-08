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
        
        # Get audio duration using ffprobe
        duration_cmd = [
            'ffprobe', 
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(input_path)
        ]
        
        duration = float(subprocess.check_output(duration_cmd).decode().strip())
        
        # Progressive compression attempts with different strategies
        compression_attempts = [
            # First attempt: Standard VBR compression with calculated bitrate
            {
                'strategy': 'vbr_bitrate',
                'safety_margin': 0.95,
                'params': lambda bitrate: ['-b:a', f'{bitrate}k', '-acodec', 'libmp3lame']
            },
            # Second attempt: More aggressive VBR with quality setting
            {
                'strategy': 'vbr_quality',
                'safety_margin': 0.90,
                'params': lambda _: ['-q:a', '5', '-acodec', 'libmp3lame']  # Quality 5 (0=best, 9=worst)
            },
            # Third attempt: Most aggressive compression
            {
                'strategy': 'max_compression',
                'safety_margin': 0.85,
                'params': lambda _: ['-q:a', '7', '-compression_level', '9', '-acodec', 'libmp3lame']
            }
        ]
        
        for attempt_num, compression in enumerate(compression_attempts, 1):
            try:
                if output_path.exists():
                    os.unlink(output_path)
                    
                target_size_bytes = max_size_mb * 1024 * 1024 * compression['safety_margin']
                
                if compression['strategy'] == 'vbr_bitrate':
                    target_bitrate = int((target_size_bytes * 8) / duration / 1000)
                    logger.info(f"Attempt {attempt_num}: VBR compression with target bitrate: {target_bitrate}kbps")
                    compression_params = compression['params'](target_bitrate)
                else:
                    logger.info(f"Attempt {attempt_num}: Using {compression['strategy']} strategy")
                    compression_params = compression['params'](None)
                
                # Use FFmpeg for compression
                compress_cmd = [
                    'ffmpeg',
                    '-y',  # Overwrite output file if exists
                    '-i', str(input_path)
                ] + compression_params + [str(output_path)]
                
                subprocess.run(compress_cmd, check=True, capture_output=True)
                
                # Verify the output size
                new_size = output_path.stat().st_size / (1024 * 1024)
                logger.info(f"Compressed file size: {new_size:.2f}MB")
                
                if new_size <= max_size_mb:
                    logger.info(f"Successfully compressed file below target size on attempt {attempt_num}")
                    return output_path
                else:
                    logger.warning(f"Attempt {attempt_num} failed to reach target size, trying next strategy...")
                    
            except Exception as e:
                logger.error(f"Compression attempt {attempt_num} failed: {e}")
                if attempt_num == len(compression_attempts):
                    raise
                continue
        
        raise Exception(f"Failed to compress file below {max_size_mb}MB after all attempts")
        
    except Exception as e:
        logger.error(f"Failed to compress audio: {e}")
        # Clean up failed output file if it exists
        if output_path.exists():
            try:
                os.unlink(output_path)
            except:
                pass
        raise

def speed_up_audio(input_path: Path, speed_factor: float = 2.0) -> Path:
    """
    Speed up audio file by the specified factor using FFmpeg
    Returns path to sped-up audio file
    
    Args:
        input_path: Path to input audio file
        speed_factor: Speed multiplication factor (2.0 = double speed)
        
    Returns:
        Path to sped-up audio file
    """
    output_path = input_path.parent / f"{input_path.stem}_x{speed_factor}{input_path.suffix}"
    
    try:
        # Check if speed factor is within FFmpeg's atempo range
        if speed_factor < 0.5 or speed_factor > 2.0:
            raise ValueError(f"Speed factor must be between 0.5 and 2.0, got {speed_factor}")
            
        logger.info(f"Speeding up audio by {speed_factor}x")
        
        # Use FFmpeg to speed up audio
        speed_cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file if exists
            '-i', str(input_path),
            '-filter:a', f'atempo={speed_factor}',
            '-vn',  # No video
            str(output_path)
        ]
        
        result = subprocess.run(speed_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg error: {result.stderr}")
            
        # Verify output exists
        if not output_path.exists():
            raise Exception("Output file was not created")
            
        original_size = input_path.stat().st_size / (1024 * 1024)
        new_size = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Created sped-up audio: {output_path.name} ({new_size:.2f}MB from {original_size:.2f}MB)")
        
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to speed up audio: {e}")
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