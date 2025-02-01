import spacy
import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
from collections import Counter
from spacy.tokens import Doc, Span
from spacy.language import Language

@dataclass
class ProcessedTranscript:
    cleaned_text: str
    entities: List[Tuple[str, str]]
    key_phrases: List[str]
    topics: List[str]
    sentiment_score: float
    questions: List[str]
    keywords: List[Tuple[str, float]]

class TranscriptPreprocessor:
    def __init__(self):
        # Load English language model with all pipeline components
        self.nlp = spacy.load("en_core_web_lg")
        
        # Add financial domain context
        self.setup_financial_context()
        
    def setup_financial_context(self):
        """Add financial domain-specific context to the NLP pipeline."""
        # Define financial terms and their expanded forms
        self.financial_terms = {
            "market": "stock market",
            "markets": "stock markets",
            "fed": "Federal Reserve",
            "rates": "interest rates",
            "curve": "yield curve",
            "basis points": "percentage points",
            "equity": "stock equity",
            "equities": "stock equities",
            "securities": "financial securities",
            "bonds": "treasury bonds",
            "treasuries": "treasury bonds",
        }
        
        # Define common financial phrases that should be kept together
        self.financial_phrases = [
            "stock market",
            "federal reserve",
            "interest rates",
            "yield curve",
            "treasury bonds",
            "basis points",
            "federal funds rate",
            "monetary policy",
            "market maker",
            "credit market",
            "bond market",
            "equity market",
            "financial literacy",
            "market dynamics",
            "market trends",
            "credit score",
            "credit rating",
            "credit worthiness",
            "debt to income ratio",
            "mortgage backed securities",
            "collateralized mortgage obligation",
        ]
        
        # Add custom pipeline component for financial context
        @Language.component("financial_context")
        def add_financial_context(doc: Doc) -> Doc:
            # Expand common abbreviations and terms
            new_ents = []
            for ent in doc.ents:
                # Check if this entity should be expanded
                lower_text = ent.text.lower()
                if lower_text in self.financial_terms:
                    new_text = self.financial_terms[lower_text]
                    new_ents.append(Span(doc, ent.start, ent.end, label="FINANCIAL_TERM", kb_id=new_text))
                else:
                    new_ents.append(ent)
            
            # Add custom entity labels
            doc.ents = new_ents
            return doc
        
        # Add the component to the pipeline
        if "financial_context" not in self.nlp.pipe_names:
            self.nlp.add_pipe("financial_context", after="ner")
        
    def clean_text(self, text: str) -> str:
        """Remove filler words and transcription artifacts."""
        # Remove timestamps if present
        text = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', text)
        
        # Remove speaker diarization markers
        text = re.sub(r'\*+\s*\w+:\s*', '', text)  # Matches patterns like "**Jess:" or "*Jessie:"
        text = re.sub(r'\s*:\s*\*+\s*', ' ', text)  # Matches remaining colons and asterisks
        
        # Remove common filler words
        filler_words = r'\b(um|uh|like|you know|sort of|kind of|basically)\b'
        text = re.sub(filler_words, '', text, flags=re.IGNORECASE)
        
        # Clean up multiple spaces and newlines
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def extract_entities(self, doc) -> List[Tuple[str, str]]:
        """Extract named entities with their labels, filtering out mentions of celebrities/companies 
        unless they are central to the discussion."""
        # Count entity frequencies
        entity_freq = Counter()
        for ent in doc.ents:
            # Use expanded forms for financial terms
            if ent.text.lower() in self.financial_terms:
                entity_freq[self.financial_terms[ent.text.lower()]] += 1
            else:
                entity_freq[ent.text.lower()] += 1
        
        # Calculate average frequency
        avg_freq = sum(entity_freq.values()) / len(entity_freq) if entity_freq else 0
        
        # Filter entities
        filtered_entities = []
        for ent in doc.ents:
            # Skip celebrity/company mentions unless they're frequently discussed
            if ent.label_ in ['PERSON', 'ORG'] and entity_freq[ent.text.lower()] < avg_freq:
                continue
            
            # Use expanded forms for financial terms
            if ent.text.lower() in self.financial_terms:
                filtered_entities.append((self.financial_terms[ent.text.lower()], "FINANCIAL_TERM"))
            else:
                filtered_entities.append((ent.text, ent.label_))
        
        return filtered_entities
    
    def extract_key_phrases(self, doc) -> List[str]:
        """Extract important noun phrases and verb phrases, with financial context."""
        key_phrases = []
        
        # First, check for financial phrases
        text_lower = doc.text.lower()
        for phrase in self.financial_phrases:
            if phrase in text_lower:
                key_phrases.append(phrase)
        
        # Then add other important noun chunks
        for chunk in doc.noun_chunks:
            if chunk.root.pos_ in ['NOUN', 'PROPN']:
                # Expand financial terms if needed
                chunk_text = chunk.text
                chunk_lower = chunk_text.lower()
                if chunk_lower in self.financial_terms:
                    chunk_text = self.financial_terms[chunk_lower]
                key_phrases.append(chunk_text)
        
        return list(set(key_phrases))
    
    def identify_topics(self, doc) -> List[str]:
        """Identify main topics using noun frequency and importance, 
        filtering out generic terms."""
        # Skip very generic terms but keep financial terms
        generic_terms = {'thing', 'things', 'way', 'ways', 
                        'time', 'times', 'example', 'examples', 'day', 'days'}
        
        topic_freq = {}
        for token in doc:
            if (token.pos_ in ['NOUN', 'PROPN'] and 
                not token.is_stop and 
                token.text.lower() not in generic_terms):
                # Use expanded forms for financial terms
                if token.text.lower() in self.financial_terms:
                    topic = self.financial_terms[token.text.lower()]
                else:
                    topic = token.text
                topic_freq[topic] = topic_freq.get(topic, 0) + 1
        
        # Return top 10 topics by frequency
        return sorted(topic_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    
    def analyze_sentiment(self, doc) -> float:
        """Perform basic sentiment analysis."""
        return sum(token.sentiment for token in doc) / len(doc)
    
    def extract_questions(self, doc) -> List[str]:
        """Identify explicit and implicit questions."""
        questions = []
        
        # Explicit questions
        for sent in doc.sents:
            if sent.text.strip().endswith('?'):
                questions.append(sent.text.strip())
            
            # Implicit questions (starting with question words)
            elif any(token.text.lower() in ['how', 'what', 'why', 'when', 'where', 'who'] 
                    for token in sent[:1]):
                questions.append(sent.text.strip())
        
        return questions
    
    def extract_keywords(self, doc) -> List[Tuple[str, float]]:
        """Extract and rank keywords by importance."""
        # Count word frequencies
        word_freq = Counter()
        for token in doc:
            if (not token.is_stop and not token.is_punct and 
                len(token.text) > 2 and token.pos_ in ['NOUN', 'PROPN', 'ADJ', 'VERB']):
                word_freq[token.text.lower()] += 1
        
        # Calculate scores based on frequency and linguistic features
        keyword_scores = {}
        max_freq = max(word_freq.values()) if word_freq else 1
        
        for token in doc:
            if token.text.lower() in word_freq:
                # Base score from frequency
                freq_score = word_freq[token.text.lower()] / max_freq
                
                # Linguistic feature bonuses
                pos_bonus = {
                    'NOUN': 1.0,
                    'PROPN': 1.2,
                    'ADJ': 0.8,
                    'VERB': 0.6
                }.get(token.pos_, 0.5)
                
                # Bonus for being part of a named entity
                ent_bonus = 1.2 if token.ent_type_ else 1.0
                
                # Bonus for being a subject or object
                dep_bonus = 1.2 if token.dep_ in ['nsubj', 'dobj', 'pobj'] else 1.0
                
                # Combine scores
                final_score = freq_score * pos_bonus * ent_bonus * dep_bonus
                
                # Store the highest score for each word
                if (token.text not in keyword_scores or 
                    final_score > keyword_scores[token.text]):
                    keyword_scores[token.text] = final_score
        
        # Sort keywords by score
        sorted_keywords = sorted(
            keyword_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_keywords
    
    def process(self, transcript: str) -> ProcessedTranscript:
        """Process the transcript and return structured data."""
        # Clean the text
        cleaned_text = self.clean_text(transcript)
        
        # Process with spaCy
        doc = self.nlp(cleaned_text)
        
        # Extract all required information
        return ProcessedTranscript(
            cleaned_text=cleaned_text,
            entities=self.extract_entities(doc),
            key_phrases=self.extract_key_phrases(doc),
            topics=[topic[0] for topic in self.identify_topics(doc)],
            sentiment_score=self.analyze_sentiment(doc),
            questions=self.extract_questions(doc),
            keywords=self.extract_keywords(doc)
        )

if __name__ == "__main__":
    # Example usage
    preprocessor = TranscriptPreprocessor()
    sample_text = "Your transcript text here..."
    result = preprocessor.process(sample_text)
    print(f"Cleaned text: {result.cleaned_text[:100]}...")
    print(f"Entities found: {result.entities[:5]}")
    print(f"Key phrases: {result.key_phrases[:5]}")
    print(f"Main topics: {result.topics[:5]}") 