from indexer import MOSDACIndexer
import textwrap
import re
from typing import List, Dict, Tuple
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from collections import Counter
import heapq

class MOSDACChatbot:
    def __init__(self):
        self.indexer = MOSDACIndexer()
        # Download required NLTK data
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')
        try:
            nltk.data.find('corpora/wordnet')
        except LookupError:
            nltk.download('wordnet')
        
        self.stop_words = set(stopwords.words('english'))
        self.lemmatizer = WordNetLemmatizer()
        self.context_history = []
        self.max_context_length = 5
    
    def preprocess_query(self, query: str) -> List[str]:
        """Process the query to extract key terms"""
        # Convert to lowercase
        query = query.lower()
        
        # Tokenize the query
        tokens = word_tokenize(query)
        
        # Remove stop words and non-alphanumeric tokens, and lemmatize
        keywords = []
        for token in tokens:
            if token.isalnum() and token not in self.stop_words:
                # Lemmatize the token
                lemma = self.lemmatizer.lemmatize(token)
                keywords.append(lemma)
        
        return keywords

    def extract_key_sentences(self, text: str, num_sentences: int = 3) -> List[str]:
        """Extract the most important sentences from text using TF-IDF like scoring"""
        sentences = sent_tokenize(text)
        if not sentences:
            return []

        # Calculate word frequencies
        word_frequencies = Counter()
        for sentence in sentences:
            words = word_tokenize(sentence.lower())
            words = [w for w in words if w.isalnum() and w not in self.stop_words]
            word_frequencies.update(words)

        # Calculate sentence scores
        sentence_scores = []
        for sentence in sentences:
            score = 0
            words = word_tokenize(sentence.lower())
            words = [w for w in words if w.isalnum() and w not in self.stop_words]
            
            for word in words:
                score += word_frequencies[word]
            
            # Normalize by sentence length
            if len(words) > 0:
                score = score / len(words)
            
            sentence_scores.append((score, sentence))

        # Get top sentences
        top_sentences = heapq.nlargest(num_sentences, sentence_scores)
        return [sentence for _, sentence in top_sentences]

    def calculate_relevance(self, doc: Dict, keywords: List[str]) -> float:
        """Calculate how relevant a document is to the query"""
        relevance = 0.0
        
        # Check title
        title = doc.get('title', '').lower()
        for keyword in keywords:
            if keyword in title:
                relevance += 3.0  # Title matches are most important
            # Check for partial matches in title
            elif any(keyword in word for word in title.split()):
                relevance += 2.0
        
        # Check description
        desc = doc.get('meta_description', '').lower()
        for keyword in keywords:
            if keyword in desc:
                relevance += 1.5
            # Check for partial matches in description
            elif any(keyword in word for word in desc.split()):
                relevance += 1.0
        
        # Check content with context awareness
        content = doc.get('text_content', '').lower()
        for keyword in keywords:
            if keyword in content:
                relevance += 0.5
                # Check if keyword appears near other keywords
                for other_keyword in keywords:
                    if other_keyword != keyword:
                        # Look for keywords within 50 characters of each other
                        if abs(content.find(keyword) - content.find(other_keyword)) < 50:
                            relevance += 0.3
        
        # Check category
        category = doc.get('category', '').lower()
        for keyword in keywords:
            if keyword in category:
                relevance += 2.0
        
        # Consider context history
        for context in self.context_history:
            context_keywords = self.preprocess_query(context)
            for keyword in context_keywords:
                if keyword in content:
                    relevance += 0.2
        
        return relevance

    def summarize_results(self, results: List[Dict], query: str) -> str:
        if not results:
            return f"I couldn't find any information about '{query}' in the MOSDAC database."
        
        # Process the query
        keywords = self.preprocess_query(query)
        
        # Calculate relevance for each result
        for doc in results:
            doc['relevance'] = self.calculate_relevance(doc, keywords)
        
        # Sort results by relevance
        results.sort(key=lambda x: x.get('relevance', 0), reverse=True)
        
        # Filter out low relevance results
        min_relevance = 0.5
        results = [doc for doc in results if doc.get('relevance', 0) >= min_relevance]
        
        if not results:
            return f"I found some results, but none were relevant enough to your query about '{query}'."
        
        # Group results by category
        categorized_results = {}
        for doc in results:
            category = doc.get('category', 'General')
            if category not in categorized_results:
                categorized_results[category] = []
            categorized_results[category].append(doc)
        
        # Build the summary
        summary = []
        summary.append(f"I found {len(results)} relevant results about your query:\n")
        
        for category, docs in categorized_results.items():
            summary.append(f"\n📌 {category.upper()}:")
            for doc in docs:
                # Format the title and description
                title = doc.get('title', 'No title')
                desc = doc.get('meta_description', 'No description available')
                content = doc.get('text_content', '')
                
                # Extract key sentences from content
                key_sentences = self.extract_key_sentences(content)
                
                # Add relevant links if available
                links = doc.get('links', [])
                relevant_links = []
                for link in links:
                    if any(keyword.lower() in link.lower() for keyword in keywords):
                        relevant_links.append(link)
                
                summary.append(f"\n• {title}")
                if desc:
                    # Wrap description to 80 characters for better readability
                    wrapped_desc = textwrap.fill(desc, width=80)
                    summary.append(f"  {wrapped_desc}")
                
                # Add key sentences from content
                if key_sentences:
                    summary.append("  Key points:")
                    for sentence in key_sentences:
                        wrapped_sentence = textwrap.fill(sentence, width=80)
                        summary.append(f"  - {wrapped_sentence}")
                
                if relevant_links:
                    summary.append("  Relevant links:")
                    for link in relevant_links[:3]:  # Show only top 3 relevant links
                        summary.append(f"  - {link}")
                
                # Add confidence score if available
                if 'relevance' in doc:
                    confidence = min(100, int(doc['relevance'] * 20))  # Convert to percentage
                    if confidence >= 50:  # Only show high confidence results
                        summary.append(f"  Confidence: {confidence}%")
        
        return "\n".join(summary)
    
    def chat(self, query: str) -> str:
        # Update context history
        self.context_history.append(query)
        if len(self.context_history) > self.max_context_length:
            self.context_history.pop(0)
        
        # Perform the search with the original query
        results = self.indexer.search(query)
        
        # If no results, try with processed keywords
        if not results:
            keywords = self.preprocess_query(query)
            if keywords:
                results = self.indexer.search(' '.join(keywords))
        
        # Get the summary
        response = self.summarize_results(results, query)
        
        return response

def main():
    chatbot = MOSDACChatbot()
    print("Welcome to MOSDAC Chatbot! Type 'exit' to quit.")
    print("Ask me anything about MOSDAC's content...\n")
    
    while True:
        query = input("You: ").strip()
        if query.lower() == 'exit':
            print("\nGoodbye!")
            break
        
        if not query:
            continue
        
        print("\nMOSDAC Chatbot:")
        response = chatbot.chat(query)
        print(response)
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main() 