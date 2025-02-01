import os
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
import sys
import yaml

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.content_gen import (
    TranscriptPreprocessor,
    BlogPostGenerator,
    FAQGenerator,
    ExcerptGenerator,
    SummaryGenerator,
    SEOMetadataGenerator
)

def parse_args():
    parser = argparse.ArgumentParser(description='Generate content from podcast transcript')
    parser.add_argument(
        '--transcript', 
        type=str,
        help='Path to transcript file'
    )
    parser.add_argument(
        '--prefix', 
        type=str,
        default='',
        help='Prefix for output directory name'
    )
    return parser.parse_args()

def setup_logging(prefix: str = ''):
    # Create output directory structure
    debug_dir = Path("debug")
    output_dir = debug_dir / "content_gen_test_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create run-specific directory with timestamp and optional prefix
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_name = f"{prefix}-{timestamp}" if prefix else timestamp
    run_dir = output_dir / dir_name
    run_dir.mkdir(exist_ok=True)
    
    # Setup file handlers
    log_file = run_dir / "process.log"
    content_file = run_dir / "generated_content.md"
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also print to console
        ]
    )
    
    return run_dir, content_file

def save_content(file_path: Path, content: dict):
    """Save generated content in markdown format."""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("# Generated Content Report\n\n")
        
        # Blog Post
        f.write("## Blog Post\n")
        f.write(f"### Title\n{content['blog_post'].title}\n\n")
        f.write("### Content\n")
        f.write(content['blog_post'].content)
        f.write("\n\n")
        
        # FAQ
        f.write("## FAQ\n")
        for item in content['faq'].items:
            f.write(f"### {item.question}\n")
            f.write(f"{item.answer}\n\n")
        
        # Excerpt
        f.write("## Excerpt\n")
        f.write(content['excerpt'].excerpt)
        f.write("\n\n")
        
        # Summary
        f.write("## Summary\n")
        f.write(content['summary'].summary)
        f.write("\n\n")
        
        # SEO Metadata
        f.write("## SEO Metadata\n")
        f.write(f"### Meta Title\n{content['seo'].meta_title}\n\n")
        f.write(f"### Meta Description\n{content['seo'].meta_description}\n\n")
        
        # Schema Markup
        f.write("### Schema Markup\n```json\n")
        f.write(json.dumps(content['seo'].schema_markup, indent=2))
        f.write("\n```\n")

def read_transcript(file_path: str) -> str:
    """Read transcript from file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    # Parse command line arguments
    args = parse_args()
    
    # Get transcript content
    if args.transcript:
        transcript_path = Path(args.transcript)
        if not transcript_path.exists():
            raise FileNotFoundError(f"Transcript file not found: {args.transcript}")
        sample_transcript = read_transcript(args.transcript)
        logging.info(f"Using transcript from file: {args.transcript}")
    else:
        # Use sample transcript if no file provided
        sample_transcript = """
        Today we're talking about artificial intelligence and its impact on business. 
        Many companies are asking: How can AI transform our operations? What are the risks?
        
        Let's dive into machine learning, a key component of AI. Machine learning allows 
        systems to learn from data without explicit programming. Companies like Google 
        and Microsoft are leading the way in developing these technologies.
        
        One important consideration is ethical AI development. We need to ensure that 
        AI systems are fair, transparent, and accountable. This raises questions about 
        bias in data and algorithmic decision-making.
        
        What about small businesses? How can they leverage AI? Cloud-based AI services 
        make it possible for companies of all sizes to benefit from these technologies.
        
        In conclusion, AI is transforming business operations across industries. The key 
        is to start small, focus on specific use cases, and scale gradually while 
        maintaining ethical considerations.
        """
        logging.info("Using sample transcript")
    
    # Setup logging and get output directory paths
    run_dir, content_file = setup_logging(args.prefix)
    logging.info("Starting content generation pipeline...")
    
    try:
        # Load config
        config_path = Path("config.yaml")
        if not config_path.exists():
            raise FileNotFoundError("config.yaml not found in project root")
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Initialize all generators
        preprocessor = TranscriptPreprocessor()
        blog_generator = BlogPostGenerator()
        faq_generator = FAQGenerator()
        excerpt_generator = ExcerptGenerator()
        summary_generator = SummaryGenerator()
        seo_generator = SEOMetadataGenerator()
        
        # Process transcript
        logging.info("Processing transcript...")
        processed_data = preprocessor.process(sample_transcript)
        logging.info(f"Found {len(processed_data.entities)} entities")
        logging.info(f"Extracted {len(processed_data.keywords)} keywords")
        logging.info(f"Identified {len(processed_data.topics)} topics")
        
        # Generate all content
        logging.info("Generating blog post...")
        blog_post = blog_generator.generate(processed_data)
        logging.info(f"Blog post generated: {len(blog_post.content.split())} words")
        
        logging.info("Generating FAQ...")
        faq_content = faq_generator.generate(processed_data)
        logging.info(f"Generated {len(faq_content.items)} FAQ items")
        
        logging.info("Generating excerpt...")
        excerpt = excerpt_generator.generate(processed_data)
        logging.info(f"Excerpt generated: {len(excerpt.excerpt)} chars")
        
        logging.info("Generating summary...")
        summary = summary_generator.generate(processed_data)
        logging.info(f"Summary generated: {summary.word_count} words")
        
        logging.info("Generating SEO metadata...")
        seo_metadata = seo_generator.generate(
            processed_data,
            blog_title=blog_post.title,
            excerpt=excerpt.excerpt
        )
        logging.info("SEO metadata generated")
        
        # Save all content
        content = {
            'blog_post': blog_post,
            'faq': faq_content,
            'excerpt': excerpt,
            'summary': summary,
            'seo': seo_metadata
        }
        
        save_content(content_file, content)
        logging.info(f"Content saved to {content_file}")
        
        # Save raw data for analysis
        debug_data = {
            'entities': processed_data.entities,
            'keywords': processed_data.keywords,
            'topics': processed_data.topics,
            'key_phrases': processed_data.key_phrases
        }
        
        analysis_file = run_dir / "content_analysis.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2)
        logging.info(f"Debug data saved to {analysis_file}")
        
        # Save input transcript for reference
        transcript_file = run_dir / "input_transcript.txt"
        with open(transcript_file, 'w', encoding='utf-8') as f:
            f.write(sample_transcript)
        logging.info(f"Input transcript saved to {transcript_file}")
        
        # Polish content using GPT
        logging.info("Polishing content with GPT...")
        from src.ai.content_gen.gpt_polish import polish_generated_content
        polished_file = run_dir / "polished_content.md"
        polish_generated_content(content_file, polished_file, config)
        logging.info(f"Polished content saved to {polished_file}")
        
        logging.info("Content generation pipeline completed successfully!")
        logging.info(f"All output files are in: {run_dir}")
        
    except Exception as e:
        logging.error(f"Error in content generation pipeline: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main() 