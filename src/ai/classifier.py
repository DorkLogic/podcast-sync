from openai import OpenAI
from utils.log_setup import setup_project_logging
logger = setup_project_logging()

class CategoryClassifierError(Exception):
    """Custom exception for category classification"""
    pass

def classify_episode_category(text: str, categories: list, config: dict) -> str:
    """
    Use OpenAI to classify episode into a category based on its name
    
    Args:
        text: Name of the episode
        categories: List of valid category names
        config: Application configuration containing OpenAI settings
        
    Returns:
        Selected category name
    """
    try:
        client = OpenAI(
            api_key=config['openai']['api_key'],
            timeout=60.0,  # Default 60 second timeout
            max_retries=2  # Retry failed requests up to 2 times
        )
        
        prompt = f"""
        Given the following podcast episode title and list of categories, determine the most appropriate category.
        
        Categories: {', '.join(categories)}
        
        Episode Title: {text}
        
        Return only the category name that best matches, exactly as written in the categories list.
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a podcast categorization assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=50,
            timeout=90  # 90 second timeout for classification
        )
        
        category = response.choices[0].message.content.strip()
        
        if category not in categories:
            raise CategoryClassifierError(f"AI returned invalid category: {category}")
            
        return category
        
    except Exception as e:
        logger.error(f"Failed to classify episode: {e}")
        raise CategoryClassifierError(f"Failed to classify episode: {e}") 