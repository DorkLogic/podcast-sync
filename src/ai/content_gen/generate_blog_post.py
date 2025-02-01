from typing import List, Dict, Optional
from dataclasses import dataclass
from .preprocess_transcript import ProcessedTranscript

@dataclass
class BlogPost:
    title: str
    content: str
    sections: List[Dict[str, str]]
    keywords_used: List[str]
    meta_description: str

class BlogPostGenerator:
    def __init__(self):
        self.target_word_count = (600, 800)  # min, max words
        self.section_count = 3  # Minimum number of sections
        
    def generate_title(self, data: ProcessedTranscript) -> str:
        """Generate an SEO-friendly title using main topics."""
        # Get main topics and keywords
        main_topics = [topic for topic in data.topics[:3] 
                      if not any(topic.lower() in kw[0].lower() for kw in data.keywords[:3])]
        main_keywords = [kw[0] for kw in data.keywords[:3]]
        
        # Combine for a compelling title
        if main_topics and main_keywords:
            title = f"Mastering {main_keywords[0]}: Understanding {', '.join(main_topics)}"
        else:
            title = f"Essential Guide to {main_keywords[0] if main_keywords else 'Finance'}: Trends and Strategies"
            
        return title[:60]  # Ensure title is not too long for SEO
    
    def create_introduction(self, data: ProcessedTranscript) -> str:
        """Create an engaging introduction with context and value proposition."""
        main_keyword = data.keywords[0][0] if data.keywords else "finance"
        key_topics = [topic for topic in data.topics[:3] 
                     if topic.lower() != main_keyword.lower()]
        
        intro = f"""Understanding the complexities of {main_keyword} requires careful consideration """
        intro += f"of various factors and their interconnections. "
        
        if key_topics:
            intro += f"This comprehensive guide explores how {', '.join(key_topics)} "
            intro += "work together to shape outcomes and influence decisions. "
        
        intro += "We'll break down key concepts, examine current trends, "
        intro += "and provide actionable insights for better understanding.\n\n"
        
        return intro
    
    def create_sections(self, data: ProcessedTranscript) -> List[Dict[str, str]]:
        """Create informative content sections with real insights."""
        sections = []
        used_topics = set()
        
        # Group related phrases by topic
        topic_phrases = {}
        for topic in data.topics[:self.section_count]:
            if topic in used_topics:
                continue
                
            relevant_phrases = [
                phrase for phrase in data.key_phrases 
                if topic.lower() in phrase.lower()
            ]
            
            if relevant_phrases:
                topic_phrases[topic] = relevant_phrases
                used_topics.add(topic)
        
        # Create sections from grouped content
        for topic, phrases in topic_phrases.items():
            content = self._generate_section_content(topic, phrases, data.keywords)
            
            # Create section title
            if any(kw[0].lower() in topic.lower() for kw in data.keywords[:3]):
                title = f"Understanding {topic} Dynamics"
            else:
                title = f"The Role of {topic}"
            
            sections.append({
                "heading": title,
                "content": content
            })
        
        return sections
    
    def _generate_section_content(
        self, 
        topic: str, 
        phrases: List[str], 
        keywords: List[tuple]
    ) -> str:
        """Generate informative section content with structure."""
        content = []
        
        # Introduction sentence
        content.append(f"{topic} plays a crucial role in shaping outcomes and strategies. ")
        
        # Key points with context
        if phrases:
            content.append("Here are key aspects to consider:\n")
            for phrase in phrases[:3]:
                content.append(f"- {phrase.capitalize()}")
            content.append("")  # Add spacing
        
        # Add context with relevant keywords
        relevant_keywords = [
            kw[0] for kw in keywords 
            if kw[0].lower() in topic.lower()
        ]
        if relevant_keywords:
            content.append(f"When analyzing {topic}, it's important to consider ")
            content.append(f"how {relevant_keywords[0]} influences decision-making ")
            content.append("and shapes long-term strategies.")
            
        return "\n".join(content)
    
    def create_conclusion(self, data: ProcessedTranscript) -> str:
        """Create an actionable conclusion with next steps."""
        main_keyword = data.keywords[0][0] if data.keywords else "finance"
        secondary_keywords = [kw[0] for kw in data.keywords[1:3]]
        
        conclusion = f"""
        Success in understanding and navigating {main_keyword} requires a holistic approach. """
        
        if secondary_keywords:
            conclusion += f"By considering factors like {', '.join(secondary_keywords)}, "
            conclusion += "you can develop more effective strategies. "
        
        conclusion += """
        Stay informed about industry trends, maintain a learning mindset, 
        and don't hesitate to seek expert guidance when needed.
        
        For more insights and detailed analysis, explore our related resources 
        or reach out to industry professionals who can provide personalized guidance.
        """
        
        return conclusion.strip()
    
    def generate(self, data: ProcessedTranscript) -> BlogPost:
        """Generate a complete blog post from processed transcript data."""
        title = self.generate_title(data)
        introduction = self.create_introduction(data)
        sections = self.create_sections(data)
        conclusion = self.create_conclusion(data)
        
        # Combine all parts into full content
        content_parts = [introduction]
        for section in sections:
            content_parts.extend([
                f"\n## {section['heading']}\n",
                section['content']
            ])
        content_parts.append(f"\n## Conclusion\n{conclusion}")
        
        full_content = "\n".join(content_parts)
        
        # Track keywords used
        keywords_used = [kw[0] for kw in data.keywords 
                        if kw[0].lower() in full_content.lower()]
        
        # Generate meta description
        meta_description = f"Master {data.topics[0] if data.topics else 'finance'} and understand "
        meta_description += f"how {data.keywords[0][0] if data.keywords else 'markets'} impact outcomes. "
        meta_description += "Expert insights and practical strategies included."
        
        return BlogPost(
            title=title,
            content=full_content,
            sections=sections,
            keywords_used=keywords_used,
            meta_description=meta_description[:155]  # SEO length limit
        )

if __name__ == "__main__":
    # Example usage
    from preprocess_transcript import TranscriptPreprocessor
    
    preprocessor = TranscriptPreprocessor()
    sample_text = "Your transcript text here..."
    processed_data = preprocessor.process(sample_text)
    
    generator = BlogPostGenerator()
    blog_post = generator.generate(processed_data)
    
    print(f"Title: {blog_post.title}")
    print(f"Content length: {len(blog_post.content.split())}")
    print(f"Keywords used: {blog_post.keywords_used}")
    print(f"Meta description: {blog_post.meta_description}") 