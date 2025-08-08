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

def generate_summary(client, transcript_text):
    """Use GPT-4 to generate a detailed meeting summary"""
    system_prompt = """You are a meeting summarizer. Given a transcript of a meeting or conversation, create a comprehensive summary that includes:

1. Key Points and Decisions
   - Main topics discussed
   - Important decisions made
   - Action items or next steps

2. Discussion Details
   - Important insights or explanations
   - Technical details discussed
   - Questions raised and answers provided

3. Follow-up Items
   - Tasks assigned
   - Open questions
   - Scheduled follow-ups

Format the summary in Markdown with appropriate headers and bullet points."""

    user_prompt = f"""Please provide a detailed summary of this meeting transcript:

{transcript_text}

Focus on capturing the essential information while maintaining clarity and organization."""

    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.1
    )
    
    return response.choices[0].message.content.strip()

def summarize_meeting(transcript_path):
    """Generate a summary from the meeting transcript"""
    if not transcript_path.exists():
        print(f"Error: Transcript file not found: {transcript_path}")
        sys.exit(1)

    # Setup output path
    output_path = transcript_path.parent / f"{transcript_path.stem}_meeting_summary.md"
    
    # Read transcript
    print(f"Reading transcript from {transcript_path}")
    with open(transcript_path, 'r', encoding='utf-8') as f:
        transcript = f.read()
    
    # Initialize OpenAI client
    config = load_config()
    client = OpenAI(api_key=config['openai']['api_key'])
    
    # Generate summary
    print("Generating meeting summary...")
    summary = generate_summary(client, transcript)
    
    # Save summary
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(summary)
    print(f"Summary saved to {output_path}")
    
    return summary

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python meeting_summarization.py <transcript.md>")
        sys.exit(1)
    
    transcript_file = Path(sys.argv[1])
    summarize_meeting(transcript_file) 