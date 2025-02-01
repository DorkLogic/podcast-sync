from typing import List, Dict
from dataclasses import dataclass
from .preprocess_transcript import ProcessedTranscript

@dataclass
class SummaryResult:
    summary: str
    keywords_used: List[str]
    key_takeaways: List[str]
    word_count: int

class SummaryGenerator:
    def __init__(self):
        self.target_length = (150, 200)  # min, max words
        self.max_takeaways = 3
        
    def _extract_key_takeaways(
        self, 
        data: ProcessedTranscript
    ) -> List[str]:
        """Extract key takeaways from the transcript data."""
        takeaways = []
        
        # Use top topics and their related phrases
        for topic in data.topics[:self.max_takeaways]:
            relevant_phrases = [
                phrase for phrase in data.key_phrases
                if topic.lower() in phrase.lower()
            ]
            
            if relevant_phrases:
                takeaway = f"{topic}: {relevant_phrases[0]}"
            else:
                # If no relevant phrase, use a keyword if available
                relevant_keywords = [
                    kw[0] for kw in data.keywords
                    if kw[0].lower() in topic.lower()
                ]
                if relevant_keywords:
                    takeaway = f"{topic} involves {relevant_keywords[0]}"
                else:
                    takeaway = f"{topic} is a key focus area"
                    
            takeaways.append(takeaway)
            
        return takeaways
    
    def _create_introduction(
        self, 
        data: ProcessedTranscript
    ) -> str:
        """Create an engaging introduction with main keyword."""
        main_keyword = data.keywords[0][0] if data.keywords else ""
        main_entity = data.entities[0][0] if data.entities else ""
        
        intro = f"In this insightful episode about {main_keyword}"
        if main_entity and main_entity != main_keyword:
            intro += f", featuring {main_entity},"
        else:
            intro += ","
            
        return intro
    
    def _create_body(
        self, 
        data: ProcessedTranscript, 
        takeaways: List[str]
    ) -> str:
        """Create the main body of the summary."""
        # Start with the key topics
        body = " we explore several crucial topics. "
        
        # Add takeaways
        if takeaways:
            body += "Key highlights include "
            body += ", ".join(takeaways[:-1])
            if len(takeaways) > 1:
                body += f", and {takeaways[-1]}"
            else:
                body += takeaways[-1]
            body += ". "
            
        return body
    
    def _create_conclusion(
        self, 
        data: ProcessedTranscript
    ) -> str:
        """Create an action-oriented conclusion."""
        # Use secondary keywords for call to action
        secondary_keywords = [kw[0] for kw in data.keywords[1:3]]
        
        conclusion = "Listeners will gain valuable insights into "
        if secondary_keywords:
            conclusion += f"{', '.join(secondary_keywords)}"
        else:
            conclusion += "these important topics"
            
        conclusion += " and practical strategies for implementation."
        
        return conclusion
    
    def generate(self, data: ProcessedTranscript) -> SummaryResult:
        """Generate a complete episode summary."""
        # Extract key takeaways first
        takeaways = self._extract_key_takeaways(data)
        
        # Generate summary components
        introduction = self._create_introduction(data)
        body = self._create_body(data, takeaways)
        conclusion = self._create_conclusion(data)
        
        # Combine all parts
        full_summary = introduction + body + conclusion
        
        # Track keywords used
        keywords_used = [
            kw[0] for kw in data.keywords
            if kw[0].lower() in full_summary.lower()
        ]
        
        # Count words
        word_count = len(full_summary.split())
        
        # Ensure length is within target range
        if word_count < self.target_length[0]:
            # Add more detail from key phrases if needed
            additional_phrases = [
                phrase for phrase in data.key_phrases
                if phrase not in full_summary
            ][:2]
            if additional_phrases:
                full_summary += f" Additional topics covered include {', '.join(additional_phrases)}."
        elif word_count > self.target_length[1]:
            # Truncate to target length while keeping complete sentences
            sentences = full_summary.split('.')
            truncated_summary = ""
            for sentence in sentences:
                if len((truncated_summary + sentence).split()) <= self.target_length[1]:
                    truncated_summary += sentence + "."
                else:
                    break
            full_summary = truncated_summary
        
        return SummaryResult(
            summary=full_summary.strip(),
            keywords_used=keywords_used,
            key_takeaways=takeaways,
            word_count=len(full_summary.split())
        )

if __name__ == "__main__":
    # Example usage
    from preprocess_transcript import TranscriptPreprocessor
    
    preprocessor = TranscriptPreprocessor()
    sample_text = "Your transcript text here..."
    processed_data = preprocessor.process(sample_text)
    
    generator = SummaryGenerator()
    result = generator.generate(processed_data)
    
    print(f"Summary ({result.word_count} words):")
    print(result.summary)
    print("\nKey takeaways:")
    for takeaway in result.key_takeaways:
        print(f"- {takeaway}")
    print(f"\nKeywords used: {result.keywords_used}") 