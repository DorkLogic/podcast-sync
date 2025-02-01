from typing import List, Tuple
from dataclasses import dataclass
from .preprocess_transcript import ProcessedTranscript

@dataclass
class ExcerptResult:
    excerpt: str
    keywords_used: List[str]
    sentiment_score: float

class ExcerptGenerator:
    def __init__(self):
        self.target_length = 73
        self.min_keywords = 1  # Minimum number of keywords to include
        
    def _get_topic_phrases(
        self, 
        data: ProcessedTranscript, 
        max_phrases: int = 2
    ) -> List[str]:
        """Get the most relevant topic phrases."""
        # Combine topics with their related key phrases
        topic_phrases = []
        for topic in data.topics[:max_phrases]:
            relevant_phrases = [
                phrase for phrase in data.key_phrases
                if topic.lower() in phrase.lower()
            ]
            if relevant_phrases:
                topic_phrases.append(relevant_phrases[0])
            else:
                topic_phrases.append(topic)
        return topic_phrases
    
    def _create_hook(
        self, 
        data: ProcessedTranscript
    ) -> Tuple[str, List[str]]:
        """Create an engaging hook with keywords."""
        # Get main keyword and entity
        main_keyword = data.keywords[0][0] if data.keywords else ""
        main_entity = data.entities[0][0] if data.entities else ""
        
        hooks = [
            f"Discover {main_keyword}",
            f"Explore {main_keyword}",
            f"Master {main_keyword}",
            f"Learn about {main_keyword}",
            f"Understand {main_keyword}"
        ]
        
        # Select hook based on sentiment
        hook_index = min(
            int(abs(data.sentiment_score * len(hooks))),
            len(hooks) - 1
        )
        
        used_keywords = [main_keyword]
        if main_entity and main_entity != main_keyword:
            used_keywords.append(main_entity)
            
        return hooks[hook_index], used_keywords
    
    def generate(self, data: ProcessedTranscript) -> ExcerptResult:
        """Generate a 73-character excerpt optimized for engagement."""
        # Create hook with main keyword
        hook, used_keywords = self._create_hook(data)
        
        # Get relevant topic phrases
        topic_phrases = self._get_topic_phrases(data)
        
        # Construct base excerpt
        excerpt = hook
        
        # Add topic information if space allows
        if topic_phrases:
            remaining_length = self.target_length - len(excerpt)
            topic_str = f": {topic_phrases[0]}"
            
            if len(topic_str) <= remaining_length:
                excerpt += topic_str
                
                # Add second topic if space allows
                if len(topic_phrases) > 1:
                    remaining_length = self.target_length - len(excerpt)
                    second_topic = f" & {topic_phrases[1]}"
                    if len(second_topic) <= remaining_length:
                        excerpt += second_topic
        
        # Ensure excerpt ends with punctuation
        if not excerpt.endswith(('.', '!', '?')):
            excerpt += '.'
            
        # Truncate to target length if necessary
        excerpt = excerpt[:self.target_length].strip()
        
        # Track keywords used
        keywords_used = [
            kw[0] for kw in data.keywords
            if kw[0].lower() in excerpt.lower()
        ]
        
        return ExcerptResult(
            excerpt=excerpt,
            keywords_used=keywords_used,
            sentiment_score=data.sentiment_score
        )

if __name__ == "__main__":
    # Example usage
    from preprocess_transcript import TranscriptPreprocessor
    
    preprocessor = TranscriptPreprocessor()
    sample_text = "Your transcript text here..."
    processed_data = preprocessor.process(sample_text)
    
    generator = ExcerptGenerator()
    result = generator.generate(processed_data)
    
    print(f"Excerpt ({len(result.excerpt)} chars): {result.excerpt}")
    print(f"Keywords used: {result.keywords_used}")
    print(f"Sentiment score: {result.sentiment_score}") 