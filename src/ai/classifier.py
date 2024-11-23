import logging
from typing import List
from openai import OpenAI

logger = logging.getLogger(__name__)

class CategoryClassifierError(Exception):
    """Custom exception for category classification"""
    pass

def classify_episode_category(transcript: str, categories: List[str], config: dict) -> str:
    """
    Use OpenAI to classify episode into a category
    
    Args:
        transcript: Episode transcript text
        categories: List of valid category names
        config: Application configuration containing OpenAI settings
        
    Returns:
        Selected category name
    """
    try:
        client = OpenAI(api_key=config['openai']['api_key'])
        
        prompt = f"""
        Given the following podcast transcript and list of categories, determine the most appropriate category.
        
        Categories: {', '.join(categories)}
        
        Transcript excerpt:
        {transcript[:2000]}  # Using first 2000 chars to stay within token limits
        
        Return only the category name that best matches, exactly as written in the categories list.
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a podcast categorization assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=50
        )
        
        category = response.choices[0].message.content.strip()
        
        if category not in categories:
            raise CategoryClassifierError(f"AI returned invalid category: {category}")
            
        return category
        
    except Exception as e:
        logger.error(f"Failed to classify episode: {e}")
        raise CategoryClassifierError(f"Failed to classify episode: {e}") 