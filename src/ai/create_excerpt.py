from openai import OpenAI
from typing import List
from utils.log_setup import setup_project_logging

logger = setup_project_logging()

class ExcerptGenerationError(Exception):
    """Custom exception for excerpt generation failures"""
    pass

def create_excerpt(tokens: List[str], desired_length: int, config: dict) -> str:
    """
    Generate a coherent excerpt from a list of tokens using OpenAI.
    
    Args:
        tokens: List of strings representing key tokens/words to include
        desired_length: Target length of the generated excerpt in characters
        config: Application configuration containing OpenAI settings
        
    Returns:
        A string containing the generated excerpt, guaranteed not to exceed desired_length
        
    Raises:
        ExcerptGenerationError: If generation fails or input is invalid
    """
    if not tokens:
        raise ExcerptGenerationError("Token list cannot be empty")
        
    if desired_length < 10:
        raise ExcerptGenerationError("Desired length must be at least 10 characters")
    
    try:
        client = OpenAI(api_key=config['openai']['api_key'])
        
        prompt = f"""
        Create a brief, engaging summary that captures the essence of this podcast episode moment.
        The summary MUST be no longer than {desired_length} characters.
        
        Using these key phrases as context: {', '.join(tokens)}
        
        Requirements:
        - Create an original summary that captures the main point or highlight
        - DO NOT directly quote or copy dialogue from the source
        - Write in third person, descriptive style
        - Focus on the key information or insight being discussed
        - Keep it STRICTLY under {desired_length} characters (including punctuation and spaces)
        - Make it engaging and informative for potential listeners
        - Use clear, concise language
        - Return only the generated summary text
        
        Example style (but with different content):
        "Exploring the impact of AI on modern healthcare systems and patient care..."
        "A fascinating look at how urban planning shapes community well-being..."
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert at creating concise, informative summaries while avoiding direct quotes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        excerpt = response.choices[0].message.content.strip()
        
        # If excerpt is too long, truncate it at the last complete word within the limit
        if len(excerpt) > desired_length:
            logger.warning(f"Truncating excerpt from {len(excerpt)} to {desired_length} characters")
            excerpt = excerpt[:desired_length]
            # Find last space before limit
            last_space = excerpt.rfind(' ')
            if last_space > 0:
                excerpt = excerpt[:last_space].rstrip()
            # Add ellipsis if we truncated mid-sentence and have room
            if excerpt[-1] not in '.!?' and len(excerpt) <= desired_length - 3:
                excerpt = excerpt.rstrip() + '...'
            # Final length check - if still too long, remove characters until we're under the limit
            while len(excerpt) > desired_length:
                if excerpt.endswith('...'):
                    excerpt = excerpt[:-4].rstrip() + '...'
                else:
                    excerpt = excerpt[:-1].rstrip()
                
        return excerpt
        
    except Exception as e:
        logger.error(f"Failed to generate excerpt: {e}")
        raise ExcerptGenerationError(f"Failed to generate excerpt: {e}") 