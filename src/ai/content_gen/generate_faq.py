from typing import List, Dict
from dataclasses import dataclass
from .preprocess_transcript import ProcessedTranscript

@dataclass
class FAQItem:
    question: str
    answer: str
    keywords: List[str]

@dataclass
class FAQContent:
    items: List[FAQItem]
    schema_markup: Dict

class FAQGenerator:
    def __init__(self):
        self.max_answer_length = 150  # Maximum characters for each answer
        self.min_questions = 3  # Minimum number of FAQ items to generate
        
    def _clean_question(self, question: str) -> str:
        """Ensure question ends with question mark and is properly formatted."""
        question = question.strip()
        if not question.endswith('?'):
            question += '?'
        return question[0].upper() + question[1:]
    
    def _generate_answer(
        self, 
        question: str, 
        data: ProcessedTranscript,
        relevant_keywords: List[str]
    ) -> str:
        """Generate a concise, informative answer using transcript data."""
        # Extract relevant phrases based on question keywords
        question_words = set(word.lower() for word in question.split())
        relevant_phrases = [
            phrase for phrase in data.key_phrases
            if any(word in phrase.lower() for word in question_words)
        ]
        
        # Construct answer using relevant information
        answer = ""
        if relevant_phrases:
            answer = relevant_phrases[0].capitalize() + ". "
        
        # Include a keyword if possible
        if relevant_keywords:
            answer += f"This relates to {relevant_keywords[0]} "
            answer += "in the broader context."
            
        return answer[:self.max_answer_length].strip()
    
    def _extract_implicit_questions(
        self, 
        data: ProcessedTranscript
    ) -> List[str]:
        """Generate questions from topics and key phrases."""
        questions = []
        
        # Generate questions from main topics
        for topic in data.topics[:3]:
            questions.append(f"What is the importance of {topic}?")
            questions.append(f"How does {topic} work?")
        
        # Generate questions from key entities
        for entity, label in data.entities[:3]:
            if label in ['PERSON', 'ORG', 'PRODUCT']:
                questions.append(f"Who is {entity} and why are they important?")
            elif label in ['CONCEPT', 'WORK_OF_ART']:
                questions.append(f"What is {entity} and why does it matter?")
                
        return questions
    
    def generate(self, data: ProcessedTranscript) -> FAQContent:
        """Generate FAQ content with schema markup."""
        faq_items = []
        
        # Combine explicit and implicit questions
        all_questions = data.questions + self._extract_implicit_questions(data)
        
        # Process each question
        for question in all_questions:
            # Clean and format question
            cleaned_question = self._clean_question(question)
            
            # Find relevant keywords for this question
            relevant_keywords = [
                kw[0] for kw in data.keywords
                if kw[0].lower() in question.lower()
            ]
            
            # Generate answer
            answer = self._generate_answer(
                question,
                data,
                relevant_keywords
            )
            
            faq_items.append(FAQItem(
                question=cleaned_question,
                answer=answer,
                keywords=relevant_keywords
            ))
        
        # Ensure minimum number of items
        while len(faq_items) < self.min_questions:
            topic = data.topics[len(faq_items)]
            question = f"What are the key aspects of {topic}?"
            answer = f"{topic} is a crucial element that involves "
            answer += f"{', '.join(data.key_phrases[:2])}."
            
            faq_items.append(FAQItem(
                question=question,
                answer=answer,
                keywords=[kw[0] for kw in data.keywords if kw[0] in topic]
            ))
        
        # Generate schema markup
        schema_markup = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": item.question,
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": item.answer
                    }
                }
                for item in faq_items
            ]
        }
        
        return FAQContent(
            items=faq_items,
            schema_markup=schema_markup
        )

if __name__ == "__main__":
    # Example usage
    from preprocess_transcript import TranscriptPreprocessor
    
    preprocessor = TranscriptPreprocessor()
    sample_text = "Your transcript text here..."
    processed_data = preprocessor.process(sample_text)
    
    generator = FAQGenerator()
    faq_content = generator.generate(processed_data)
    
    print(f"Generated {len(faq_content.items)} FAQ items")
    for item in faq_content.items[:2]:
        print(f"\nQ: {item.question}")
        print(f"A: {item.answer}")
        print(f"Keywords: {item.keywords}") 