from typing import List, Dict
from dataclasses import dataclass
from .preprocess_transcript import ProcessedTranscript

@dataclass
class SEOMetadata:
    meta_title: str
    meta_description: str
    keywords_used: List[str]
    schema_markup: Dict

class SEOMetadataGenerator:
    def __init__(self):
        self.title_max_length = 60
        self.description_max_length = 155
        self.min_keywords = 2
        
    def _create_title(
        self, 
        data: ProcessedTranscript,
        blog_title: str = None
    ) -> str:
        """Create an SEO-optimized meta title."""
        # Use blog title if provided, otherwise create from keywords
        if blog_title:
            base_title = blog_title
        else:
            main_keyword = data.keywords[0][0] if data.keywords else ""
            main_topic = data.topics[0] if data.topics else ""
            
            base_title = f"{main_keyword}: {main_topic}"
            
        # Add brand/podcast name if space allows
        remaining_length = self.title_max_length - len(base_title)
        if remaining_length > 15:  # Minimum space for brand
            base_title += " | Your Podcast Name"
            
        return base_title[:self.title_max_length]
    
    def _create_description(
        self,
        data: ProcessedTranscript,
        excerpt: str = None
    ) -> str:
        """Create an SEO-optimized meta description."""
        if excerpt and len(excerpt) <= self.description_max_length:
            base_description = excerpt
        else:
            # Create from keywords and topics
            main_keyword = data.keywords[0][0] if data.keywords else ""
            main_topics = data.topics[:2]
            
            base_description = f"Discover {main_keyword} "
            if main_topics:
                base_description += f"and learn about {', '.join(main_topics)}. "
                
            # Add call to action
            base_description += "Listen now for expert insights and practical tips."
            
        return base_description[:self.description_max_length]
    
    def _create_schema_markup(
        self,
        title: str,
        description: str,
        data: ProcessedTranscript
    ) -> Dict:
        """Create schema.org markup for the podcast episode."""
        return {
            "@context": "https://schema.org",
            "@type": "PodcastEpisode",
            "name": title,
            "description": description,
            "keywords": [kw[0] for kw in data.keywords[:5]],
            "about": [
                {
                    "@type": "Thing",
                    "name": topic
                }
                for topic in data.topics[:3]
            ]
        }
    
    def generate(
        self,
        data: ProcessedTranscript,
        blog_title: str = None,
        excerpt: str = None
    ) -> SEOMetadata:
        """Generate complete SEO metadata."""
        # Create meta title
        meta_title = self._create_title(data, blog_title)
        
        # Create meta description
        meta_description = self._create_description(data, excerpt)
        
        # Track keywords used
        keywords_used = [
            kw[0] for kw in data.keywords
            if kw[0].lower() in meta_title.lower() or 
            kw[0].lower() in meta_description.lower()
        ]
        
        # Ensure minimum keyword usage
        if len(keywords_used) < self.min_keywords:
            # Try to incorporate more keywords in description
            remaining_keywords = [
                kw[0] for kw in data.keywords
                if kw[0] not in keywords_used
            ]
            
            if remaining_keywords:
                additional_text = f" Learn about {remaining_keywords[0]}."
                if len(meta_description) + len(additional_text) <= self.description_max_length:
                    meta_description += additional_text
                    keywords_used.append(remaining_keywords[0])
        
        # Create schema markup
        schema_markup = self._create_schema_markup(
            meta_title,
            meta_description,
            data
        )
        
        return SEOMetadata(
            meta_title=meta_title,
            meta_description=meta_description,
            keywords_used=keywords_used,
            schema_markup=schema_markup
        )

if __name__ == "__main__":
    # Example usage
    from preprocess_transcript import TranscriptPreprocessor
    
    preprocessor = TranscriptPreprocessor()
    sample_text = "Your transcript text here..."
    processed_data = preprocessor.process(sample_text)
    
    generator = SEOMetadataGenerator()
    metadata = generator.generate(processed_data)
    
    print(f"Meta Title ({len(metadata.meta_title)} chars):")
    print(metadata.meta_title)
    print(f"\nMeta Description ({len(metadata.meta_description)} chars):")
    print(metadata.meta_description)
    print(f"\nKeywords used: {metadata.keywords_used}")
    print("\nSchema Markup:")
    print(metadata.schema_markup) 