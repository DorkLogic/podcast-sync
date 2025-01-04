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
        Create a complete, SEO-friendly podcast episode description that will attract listeners.
        The description MUST be exactly {desired_length} characters or less.
        
        Using these key phrases as context: {', '.join(tokens)}
        
        Requirements:
        1. Write a COMPLETE sentence or thought - never end mid-sentence
        2. Focus on the main value or insight listeners will gain
        3. Use active, engaging language that makes people want to listen
        4. Include specific topics or themes being discussed
        5. Keep it EXACTLY {desired_length} characters or less (including punctuation and spaces)
        6. Make it work well for podcast directories and search
        7. Use clear, professional language
        8. Return only the generated description text
        
        Example format (but with different content):
        "Expert insights on scaling SaaS businesses through strategic partnerships and AI automation."
        "Breaking down the latest fintech trends and their impact on retail banking and investments."
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert at writing engaging, complete podcast descriptions that work well for SEO and discovery."},
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