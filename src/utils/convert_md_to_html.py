#!/usr/bin/env python3
import markdown
import logging
import yaml
from pathlib import Path
import re

logger = logging.getLogger(__name__)

def load_config() -> dict:
    """Load configuration from config.yaml"""
    try:
        config_path = Path(__file__).parent.parent.parent / 'config.yaml'
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise

def normalize_host_names(content: str, config: dict) -> str:
    """
    Replace any variations of host names with their correct spellings from config
    """
    try:
        # Get correct host names from config
        host1_full = config['hosts']['host1']['name']
        host1_short = config['hosts']['host1']['short_name']
        host2_full = config['hosts']['host2']['name']
        host2_short = config['hosts']['host2']['short_name']
        
        # Common variations to replace (add more as needed)
        replacements = {
            'Jessi Denwey': host2_full,
            'Jessi': host2_short,
            'Jessie': host2_short,
            'Jess': host2_short,
            'Jessica Inskip': host1_full,
            'Jessica': host1_short,
            'Jess': host1_short,
        }
        
        # Replace all variations, being careful with case sensitivity
        for wrong, correct in replacements.items():
            # Replace variations within speaker labels
            content = re.sub(
                f'\\*\\*{wrong}:\\*\\*',
                f'**{correct}:**',
                content,
                flags=re.IGNORECASE
            )
            # Replace variations in regular text
            content = re.sub(
                f'\\b{wrong}\\b',
                correct,
                content,
                flags=re.IGNORECASE
            )
            
        return content
        
    except Exception as e:
        logger.error(f"Error normalizing host names: {e}")
        raise

def convert_markdown_to_html(markdown_path: Path) -> str:
    """
    Convert markdown content to HTML, with special handling for podcast transcripts
    """
    try:
        logger.info("Converting markdown content to HTML...")
        
        # Load config for host names
        config = load_config()
        
        # Read markdown content
        with open(markdown_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Normalize host names before any other processing
        content = normalize_host_names(content, config)
            
        # Pre-process speaker labels before markdown conversion
        # Replace **Speaker:** with <strong>Speaker:</strong>
        content = content.replace('**', '<strong>', 1).replace('**', '</strong>', 1) if '**' in content else content
        
        # Convert markdown to HTML
        html = markdown.markdown(content)
        
        # Post-process any remaining markdown-style speaker labels
        html = html.replace('**', '<strong>')  # Replace remaining ** with <strong>
        
        logger.info("Successfully converted markdown to HTML")
        return html
        
    except Exception as e:
        logger.error(f"Failed to convert markdown to HTML: {e}")
        raise

def save_html(html_content: str, output_path: Path) -> None:
    """
    Save HTML content to file
    
    Args:
        html_content (str): HTML string to save
        output_path (Path): Path to save HTML file
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"Saved HTML to {output_path}")
    except Exception as e:
        logger.error(f"Error saving HTML: {e}")
        raise

def main():
    """
    Command line utility to convert markdown to HTML
    """
    import sys
    if len(sys.argv) < 2:
        print("Usage: convert_md_to_html.py <markdown_file>")
        sys.exit(1)
        
    markdown_path = Path(sys.argv[1])
    if not markdown_path.exists():
        print(f"File not found: {markdown_path}")
        sys.exit(1)
        
    html_path = markdown_path.with_suffix('.html')
    
    try:
        html_content = convert_markdown_to_html(markdown_path)
        save_html(html_content, html_path)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 