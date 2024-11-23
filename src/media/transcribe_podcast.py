#!/usr/bin/env python3
import yaml
import logging
import os
import sys
from openai import OpenAI
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Define directory paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent.parent

def load_config() -> dict:
    """Load configuration from config.yaml"""
    try:
        config_path = ROOT_DIR / 'config.yaml'
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise

def format_transcript(transcript: str) -> str:
    """Format transcript into HTML paragraphs"""
    paragraphs = transcript.split('\n\n')
    formatted_paragraphs = [f'<p id="">{p.strip()}</p>' for p in paragraphs if p.strip()]
    return '\n'.join(formatted_paragraphs)

def transcribe_audio_file(client: OpenAI, file_path: str) -> str:
    """
    Transcribe audio file using OpenAI Whisper API or load existing transcript
    Returns formatted HTML transcript
    """
    try:
        # Check for existing transcript
        transcript_path = Path(file_path).with_suffix('.html')
        if transcript_path.exists():
            logger.info(f"Found existing transcript at {transcript_path}")
            with open(transcript_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        logger.info("No existing transcript found, transcribing with OpenAI...")
        
        # Get new transcript from OpenAI
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            
        # Format transcript into HTML
        formatted_transcript = format_transcript(transcript.text)
        
        # Save HTML transcript next to audio file
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(formatted_transcript)
            
        logger.info(f"Saved new HTML transcript to {transcript_path}")
        
        return formatted_transcript
        
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        raise

def main():
    """Main function to orchestrate the transcription process"""
    try:
        # Load config and initialize OpenAI client
        config = load_config()
        client = OpenAI(api_key=config['openai']['api_key'])
        
        # Setup paths
        audio_dir = ROOT_DIR / 'debug' / 'audio'
        if not audio_dir.exists():
            raise ValueError(f"Audio directory not found: {audio_dir}")
        
        # Get audio file from command line or use first MP3 in directory
        if len(sys.argv) > 1:
            audio_file = audio_dir / sys.argv[1]
        else:
            mp3_files = list(audio_dir.glob('*.mp3'))
            if not mp3_files:
                raise ValueError(f"No MP3 files found in {audio_dir}")
            audio_file = mp3_files[0]
            
        if not audio_file.exists():
            raise ValueError(f"Audio file not found: {audio_file}")
            
        logger.info(f"Processing audio file: {audio_file.name}")
        
        # Transcribe audio and save HTML
        transcript = transcribe_audio_file(client, str(audio_file))
        logger.info("Transcription complete")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 