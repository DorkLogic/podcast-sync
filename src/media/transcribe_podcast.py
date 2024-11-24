#!/usr/bin/env python3
import yaml
import logging
import os
import sys
from openai import OpenAI
from pathlib import Path
from utils.convert_md_to_html import convert_markdown_to_html
import json

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

def format_conversation(transcript: str, config: dict) -> str:
    """
    Format transcript into a conversation-style format with speaker labels.
    Uses host names from config file.
    """
    try:
        # Get host names from config
        host1 = config['hosts']['host1']['short_name']
        host2 = config['hosts']['host2']['short_name']
        
        sentences = transcript.split(". ")
        conversation = []
        speaker_toggle = True

        for sentence in sentences:
            if not sentence.strip():
                continue
            # Use configured host names instead of hardcoded values
            speaker = host1 if speaker_toggle else host2
            conversation.append(f"**{speaker}:** {sentence.strip()}.")
            speaker_toggle = not speaker_toggle

        return "\n\n".join(conversation)
    except Exception as e:
        logger.error(f"Error formatting conversation: {e}")
        raise

def generate_questions(client: OpenAI, conversation_text: str, output_path: Path):
    """
    Generate 10-15 questions and answers based on the conversation text.
    Save the questions and answers to a Markdown file.
    """
    try:
        logger.info("Generating summary questions and answers...")
        system_prompt = (
            "You are a helpful assistant that generates comprehensive questions and answers "
            "to test understanding of the technical concepts in the podcast content. Create 10-15 questions that cover the "
            "main points and key insights from the conversation. Format each Q&A pair as:\n\n"
            "Q: <question>\n"
            "A: <answer>\n\n"
            "Do not include any headers or additional formatting."
        )
        
        user_prompt = (
            "Based on the following conversation, generate 10-15 questions with corresponding answers "
            "to summarize the main points and test comprehension of the technical concepts. Format each as "
            "'Q: <question>' followed by 'A: <answer>' on new lines. Do not include any headers or additional text.\n\n"
            f"{conversation_text}"
        )

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5
        )

        questions_and_answers = response.choices[0].message.content.strip()

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(questions_and_answers)

        logger.info(f"Saved questions and answers to {output_path}")
        
    except Exception as e:
        logger.error(f"Error generating questions: {e}")
        raise

def transcribe_audio_file(client: OpenAI, file_path: str, config: dict) -> str:
    """
    Transcribe audio file using OpenAI Whisper API or load existing transcript
    Returns formatted conversation-style transcript
    """
    try:
        # Check for existing transcript
        transcript_path = Path(file_path).with_suffix('.md')  # Save as Markdown
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
            
        # Format transcript into conversational style using config
        formatted_transcript = format_conversation(transcript.text, config)
        
        # Save Markdown transcript next to audio file
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(formatted_transcript)
            
        logger.info(f"Saved new Markdown transcript to {transcript_path}")
        
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
        audio_dir.mkdir(exist_ok=True)
        
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
        
        # Get transcript (either from existing file or by transcribing)
        conversation_text = transcribe_audio_file(client, str(audio_file), config)
        
        # Generate questions and answers based on the transcript
        question_file_path = audio_dir / f"{audio_file.stem}-questions.md"
        logger.info("Generating questions and answers...")
        generate_questions(client, conversation_text, question_file_path)
        logger.info(f"Questions and answers saved to {question_file_path}")
        
        # Convert transcript markdown to HTML
        transcript_md_path = Path(audio_file).with_suffix('.md')
        if not transcript_md_path.exists():
            logger.error(f"Transcript markdown file not found: {transcript_md_path}")
            raise FileNotFoundError(f"Transcript markdown file not found: {transcript_md_path}")
            
        logger.info(f"Converting markdown to HTML from {transcript_md_path}")
        transcript_html = convert_markdown_to_html(transcript_md_path)
        
        # Save HTML version
        html_path = Path(audio_file).with_suffix('.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(transcript_html)
        logger.info(f"Saved HTML transcript to {html_path}")
        
        # Update webflow publish request with HTML transcript
        webflow_request_path = ROOT_DIR / 'debug' / 'network' / 'webflow_publish_request.json'
        if webflow_request_path.exists():
            logger.info("Updating webflow publish request...")
            with open(webflow_request_path, 'r', encoding='utf-8') as f:
                webflow_data = json.load(f)
            
            # Update the transcript field with HTML content
            if 'fieldData' in webflow_data and 'episode-transcript' in webflow_data['fieldData']:
                webflow_data['fieldData']['episode-transcript'] = transcript_html
                logger.info("Updated transcript field with HTML content")
                
                # Save updated request with pretty printing
                with open(webflow_request_path, 'w', encoding='utf-8') as f:
                    json.dump(webflow_data, f, indent=2, ensure_ascii=False)
                logger.info("Saved updated webflow publish request")
            else:
                logger.error("Could not find episode-transcript field in webflow request data")
        
        logger.info("All tasks complete")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
