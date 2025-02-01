import os
from typing import Dict, Optional
from dataclasses import dataclass
from pathlib import Path
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

@dataclass
class PolishedContent:
    blog_post: str
    faq: str
    excerpt: str
    summary: str
    meta_description: str

class ContentPolisher:
    def __init__(self, config: dict):
        """Initialize with OpenAI client from config."""
        self.client = OpenAI(api_key=config['openai']['api_key'])
        
        # Load prompt templates
        self.load_prompts()
    
    def load_prompts(self):
        """Load prompt templates for different content types."""
        base_context = """You are writing about U.S. financial markets and institutions:
        - When discussing "the market", you're specifically talking about the U.S. stock market
        - When discussing "the Fed", you're referring to the U.S. Federal Reserve
        - When discussing interest rates, you're talking about U.S. interest rates
        - This is a financial education podcast for U.S. investors and consumers
        """
        
        self.prompts = {
            'blog': f"""{base_context}
            You are an expert U.S. financial markets writer specializing in making complex topics accessible.
            Your task is to completely rewrite this blog post into a high-quality, educational piece about U.S. financial markets:

            REQUIREMENTS:
            1. Title:
               - Must reference specific U.S. financial markets or institutions
               - Examples: "Understanding the U.S. Stock Market" or "How the Federal Reserve Influences Interest Rates"
               - Never use generic "Market" - always specify which market
               - Maximum 60 characters
            
            2. Language and Style:
               - Use precise U.S. market terminology: "the U.S. stock market", "the Federal Reserve", "the Treasury yield curve"
               - Write for a U.S. audience familiar with basic financial terms
               - Every sentence must provide concrete value about U.S. markets or financial systems
            
            3. Content Structure:
               - Start with current U.S. market context
               - Each paragraph must connect to U.S. financial markets or institutions
               - Show relationships (e.g., how Federal Reserve decisions affect market rates)
               - Include real-world implications for U.S. investors
            
            4. Absolutely Forbidden:
               - No generic market references
               - No vague financial concepts
               - No non-U.S. market discussion unless explicitly comparing
            
            5. Required Elements:
               - Current U.S. market data or trends
               - Specific Federal Reserve policies or actions
               - Practical implications for U.S. investors
               - Expert insights about U.S. markets
            
            Original content:
            {{content}}
            """,
            
            'faq': f"""{base_context}
            You are a U.S. financial markets educator. These questions are from a podcast about U.S. financial markets and monetary policy.
            Your task is to answer questions specifically about the U.S. financial system:

            REQUIREMENTS:
            1. Every Answer Must:
               - Focus on U.S. markets and institutions
               - Include current U.S. market examples
               - Reference specific U.S. financial concepts
               - Use precise terminology ("the U.S. stock market", "the Federal Reserve")
            
            2. Structure Each Answer:
               - State the U.S.-specific context
               - Explain the U.S. market mechanics
               - Give a current U.S. market example
               - Provide practical takeaway for U.S. investors
            
            Original FAQs:
            {{content}}
            """,
            
            'excerpt': f"""{base_context}
            You are a U.S. financial markets content specialist.
            Your task is to write a powerful 73-character excerpt about U.S. financial markets:

            REQUIREMENTS:
            1. Must Include:
               - Specific U.S. market insight (e.g., "U.S. stocks rally on Fed policy shift")
               - Current U.S. market context
               - Clear value proposition for U.S. investors
            
            2. Must Not:
               - Use generic terms like "Market" or "stocks"
               - Be vague about which market (always specify "U.S.")
               - Use unnecessary words like "discover" or "explore"
            
            3. Style:
               - Active voice with strong verbs
               - Lead with the most important U.S. market insight
               - Include specific numbers or trends when possible
               - Exactly 73 characters
            
            4. Examples of Good Excerpts:
               - "U.S. stocks surge 2% as Federal Reserve signals 2024 rate cuts | Latest market analysis"
               - "How Treasury yields shape U.S. mortgage rates: Federal Reserve policy impact explained"
            
            Original excerpt:
            {{content}}
            """,
            
            'summary': f"""{base_context}
            You are a U.S. financial markets analyst.
            Your task is to summarize key insights about U.S. markets and monetary policy:

            REQUIREMENTS:
            1. Structure:
               - Lead with current U.S. market context
               - Include specific Federal Reserve actions or policies
               - Connect to U.S. investor implications
               - Maximum 4 paragraphs
            
            2. Must Include:
               - Precise U.S. market terminology
               - Current U.S. market data or rates
               - Federal Reserve policy impacts
               - Action items for U.S. investors
            
            3. Absolutely Forbidden:
               - No generic market references
               - No vague financial concepts
               - No non-U.S. market discussion
               - No "listeners will learn" phrases
            
            Original summary:
            {{content}}
            """,
            
            'meta': f"""{base_context}
            You are a U.S. financial markets SEO specialist.
            Your task is to write metadata specifically about U.S. markets and monetary policy:

            REQUIREMENTS:
            1. Meta Title:
               - Must specify U.S. market context
               - Examples: "Understanding the U.S. Stock Market" or "Federal Reserve Rate Decisions"
               - Never use generic "Market"
               - Maximum 60 characters
            
            2. Meta Description:
               - Specify U.S. market context
               - Focus on value for U.S. investors
               - Include specific market insight
               - Maximum 155 characters
            
            3. Absolutely Forbidden:
               - No generic market terms
               - No vague financial concepts
               - No non-U.S. market references
               - No keyword stuffing
            
            Original metadata:
            {{content}}
            """
        }
    
    def polish_section(self, content: str, section_type: str) -> str:
        """Polish a specific section using GPT."""
        prompt = self.prompts[section_type].format(content=content)
        
        system_message = """You are an expert U.S. financial markets content editor.
        Your primary focus is the U.S. stock market, U.S. Treasury market, and Federal Reserve policy.
        
        CRITICAL REQUIREMENTS:
        1. Never use abbreviated terms:
           - Write "the Federal Reserve" not "the Fed"
           - Write "the U.S. stock market" not "the market"
           - Write "the S&P 500 index" not "the S&P"
        
        2. Never use placeholder values:
           - If you don't have exact numbers, use ranges or recent trends
           - Example: "Treasury yields between 4.5% and 4.7%" instead of "X%"
           - Example: "stocks up 2% this month" instead of "stocks up X%"
        
        3. Always maintain precise U.S. market context:
           - Specify which U.S. market you're discussing
           - Include relevant U.S. economic context
           - Reference specific U.S. financial institutions
        
        4. Use proper financial terminology:
           - "basis points" not "bps"
           - "Federal Funds Rate" not "Fed Rate"
           - "U.S. Treasury securities" not "Treasuries"
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4-1106-preview",  # Latest GPT-4 model as of 2024
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        return response.choices[0].message.content.strip()
    
    def polish_content(self, content: Dict[str, str]) -> PolishedContent:
        """Polish all content sections."""
        return PolishedContent(
            blog_post=self.polish_section(content['blog_post'], 'blog'),
            faq=self.polish_section(content['faq'], 'faq'),
            excerpt=self.polish_section(content['excerpt'], 'excerpt'),
            summary=self.polish_section(content['summary'], 'summary'),
            meta_description=self.polish_section(content['meta_description'], 'meta')  # Now polish meta description
        )

    def write_polished_content(self, output_file: Path, polished: PolishedContent):
        """Write polished content to file with proper formatting."""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Polished Content Report\n\n")
            
            # Blog Post
            f.write("## Blog Post\n")
            if '\nTITLE:' in polished.blog_post:
                title, content = polished.blog_post.split('\nTITLE:', 1)
                f.write(f"### Title\n{title.strip()}\n\n### Content\n{content.strip()}\n")
            else:
                f.write(polished.blog_post)
            
            # FAQ
            f.write("\n## FAQ\n")
            faq_content = polished.faq.strip()
            if faq_content:
                qa_pairs = [pair.strip() for pair in faq_content.split('\n\n') if pair.strip()]
                for pair in qa_pairs:
                    lines = pair.split('\n')
                    if len(lines) >= 2:  # Must have both question and answer
                        question = lines[0].strip()
                        answer = ' '.join(line.strip() for line in lines[1:]).strip()
                        if question and answer:
                            if not question.endswith('?'):
                                question += '?'
                            f.write(f"### {question}\n{answer}\n\n")
            
            # Excerpt
            f.write("## Excerpt\n")
            f.write(polished.excerpt.strip())
            
            # Summary
            f.write("\n\n## Summary\n")
            f.write(polished.summary.strip())
            
            # Meta Description
            f.write("\n\n## SEO Metadata\n")
            meta_lines = polished.meta_description.strip().split('\n')
            title = ""
            description = ""
            for line in meta_lines:
                line = line.strip()
                if line.startswith("Title:"):
                    title = line.split(":", 1)[1].strip()
                elif line.startswith("Description:"):
                    description = line.split(":", 1)[1].strip()
            
            if title:
                f.write(f"### Meta Title\n{title}\n\n")
            if description:
                f.write(f"### Meta Description\n{description}\n\n")
            
            # Don't write the schema markup unless specifically requested

    def generate_excerpt(self, text: str, max_tokens: int = 14000) -> str:
        """
        Generate an excerpt from text, handling long inputs by chunking if needed.
        
        Args:
            text: Input text to generate excerpt from
            max_tokens: Maximum tokens to send in one request
            
        Returns:
            Generated excerpt
        """
        try:
            # Take just the first ~4000 words for excerpt generation
            # This is a very conservative limit to ensure we stay well under token limits
            words = text.split()[:4000]
            truncated_text = ' '.join(words)
            
            if len(words) < len(text.split()):
                logger.info(f"Input text truncated from {len(text.split())} to {len(words)} words for excerpt generation")
                
            # Use the existing excerpt prompt template with truncated text
            prompt = self.prompts['excerpt'].format(content=truncated_text)
            
            response = self.client.chat.completions.create(
                model="gpt-4-1106-preview",  # Latest GPT-4 model as of 2024
                messages=[
                    {"role": "system", "content": "You are a U.S. financial markets content specialist."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Failed to generate excerpt: {str(e)}")
            raise Exception(f"Failed to generate excerpt: {str(e)}")

def polish_generated_content(input_file: Path, output_file: Path, config: dict):
    """Polish content from a generated markdown file."""
    # Read the input file
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract sections
    sections = extract_sections(content)
    
    # Polish content
    polisher = ContentPolisher(config)
    polished = polisher.polish_content(sections)
    
    # Write polished content with proper formatting
    polisher.write_polished_content(output_file, polished)

def extract_sections(content: str) -> Dict[str, str]:
    """Extract sections from markdown content."""
    sections = {}
    current_section = None
    current_content = []
    
    # Split content into lines and group them
    lines = []
    for line in content.split('\n'):
        if line.strip() or lines:  # Skip leading empty lines only
            lines.append(line)
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check for main section headers
        if line.startswith('## '):
            # Save previous section if it exists
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()
                current_content = []
            
            # Extract section name
            section_name = line[3:].lower().strip()
            if section_name == 'blog post':
                current_section = 'blog_post'
                # Skip until we find the title
                while i < len(lines) and not lines[i].startswith('### Title'):
                    i += 1
                if i < len(lines):
                    current_content.append('TITLE:')
                    i += 1  # Skip the "### Title" line
            elif section_name == 'faq':
                current_section = 'faq'
            elif section_name == 'excerpt':
                current_section = 'excerpt'
            elif section_name == 'summary':
                current_section = 'summary'
            elif section_name == 'seo metadata':
                current_section = 'meta_description'
            else:
                current_section = None
        
        # Handle FAQ questions and answers
        elif current_section == 'faq' and line.startswith('### '):
            # Start a new FAQ item
            if current_content:
                current_content.append('')  # Add spacing between items
            question = line[4:].strip()
            current_content.append(question)
            
            # Collect the answer (all lines until next question or section)
            answer_lines = []
            i += 1
            while i < len(lines):
                if lines[i].startswith('### ') or lines[i].startswith('## '):
                    i -= 1  # Back up so we process this line again
                    break
                if lines[i].strip():
                    answer_lines.append(lines[i].strip())
                i += 1
            if answer_lines:
                current_content.append('  ' + ' '.join(answer_lines))
        
        # Handle blog content
        elif current_section == 'blog_post' and line.startswith('### Content'):
            i += 1  # Skip the "### Content" line
            continue
        
        # Handle metadata
        elif current_section == 'meta_description':
            if line.startswith('### Meta Title'):
                i += 1  # Skip the header
                if i < len(lines):
                    current_content.append(f"Title: {lines[i].strip()}")
            elif line.startswith('### Meta Description'):
                i += 1  # Skip the header
                if i < len(lines):
                    current_content.append(f"Description: {lines[i].strip()}")
        
        # Add content lines
        elif current_section and not line.startswith('#'):
            current_content.append(line)
        
        i += 1
    
    # Save the last section
    if current_section:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections

if __name__ == "__main__":
    # Example usage
    input_file = Path("debug/content_gen_test_output/latest/generated_content.md")
    output_file = Path("debug/content_gen_test_output/latest/polished_content.md")
    polish_generated_content(input_file, output_file) 