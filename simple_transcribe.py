#!/usr/bin/env python3
import sys
from pathlib import Path
from openai import OpenAI
import yaml

def load_config():
    """Load OpenAI API key from config.yaml"""
    config_path = Path('config.yaml')
    if not config_path.exists():
        print("Error: config.yaml not found")
        sys.exit(1)
    with open(config_path) as f:
        return yaml.safe_load(f)

def identify_speakers(client, transcript_text):
    """Use GPT-4 to identify speakers and format the transcript"""
    system_prompt = """You are a transcript formatter. Given a raw podcast transcript, identify different speakers and format the transcript as a conversation.
    - Label speakers as Speaker 1, Speaker 2, etc. consistently throughout
    - Each speaker's line should start with "**Speaker N:**"
    - Put a blank line between different speakers' turns
    - Maintain the natural flow of conversation
    - If you're unsure about a speaker change, err on the side of keeping it as the same speaker
    - Focus on clear speaker transitions in the conversation flow"""

    user_prompt = f"""Please format this podcast transcript into a conversation with speaker labels:

{transcript_text}

Format each line as "**Speaker N:** text" with blank lines between speakers. Be consistent with speaker numbers."""

    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.1
    )
    
    return response.choices[0].message.content.strip()

def transcribe_audio(file_path):
    """Transcribe audio file using OpenAI Whisper API and format with speaker identification"""
    config = load_config()
    client = OpenAI(api_key=config['openai']['api_key'])
    
    # Get output paths for raw and formatted transcripts
    raw_output = Path(file_path).with_suffix('.raw.txt')
    formatted_output = Path(file_path).with_suffix('.md')
    
    # Check for existing raw transcript
    if raw_output.exists():
        print(f"Found existing raw transcript at {raw_output}")
        with open(raw_output, 'r', encoding='utf-8') as f:
            transcript = f.read()
    else:
        print(f"Transcribing {file_path}...")
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        
        # Save raw transcript
        with open(raw_output, 'w', encoding='utf-8') as f:
            f.write(transcript)
        print(f"Raw transcript saved to {raw_output}")
    
    # Use GPT-4 to identify speakers and format transcript
    print("Identifying speakers and formatting transcript...")
    formatted_transcript = identify_speakers(client, transcript)
    
    # Save formatted transcript
    with open(formatted_output, 'w', encoding='utf-8') as f:
        f.write(formatted_transcript)
    print(f"Formatted transcript saved to {formatted_output}")
    
    return formatted_transcript

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python simple_transcribe.py <audio_file>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    if not Path(audio_file).exists():
        print(f"Error: File not found: {audio_file}")
        sys.exit(1)
        
    transcribe_audio(audio_file) 