"""
Intent routing module for LLM Chatbot.

This module provides intent classification functionality to route user queries
to appropriate workflows (summarization, question-answering, or general chat).
"""

from typing import List
from src.conversation import Intent


class IntentRouter:
    """Classifies user queries into intent categories using keyword matching.
    
    Routes queries to specialized workflows based on detected keywords:
    - SUMMARIZATION: For summary/key points requests
    - QUESTION_ANSWERING: For questions requiring specific answers
    - GENERAL_CHAT: Default conversational fallback
    
    Classification completes within 100ms using simple keyword matching.
    """
    
    # Keyword lists for intent classification
    SUMMARIZATION_KEYWORDS = ["summarize", "summary", "key points", "tldr"]
    QA_KEYWORDS = ["what", "why", "how", "when", "where", "who", "explain"]
    
    def classify_intent(self, query: str) -> Intent:
        """Classify user query into an intent category.
        
        Uses keyword matching to determine the most appropriate workflow:
        1. Check for summarization keywords
        2. Check for question-answering keywords
        3. Default to general chat
        
        Args:
            query: User input text to classify
            
        Returns:
            Intent enum value (SUMMARIZATION, QUESTION_ANSWERING, or GENERAL_CHAT)
        """
        # Check for summarization intent
        if self._contains_keywords(query, self.SUMMARIZATION_KEYWORDS):
            return Intent.SUMMARIZATION
        
        # Check for question-answering intent
        if self._contains_keywords(query, self.QA_KEYWORDS):
            return Intent.QUESTION_ANSWERING
        
        # Default to general chat
        return Intent.GENERAL_CHAT
    
    def _contains_keywords(self, query: str, keywords: List[str]) -> bool:
        """Check if query contains any of the specified keywords (case-insensitive).
        
        Args:
            query: User input text to search
            keywords: List of keywords to match
            
        Returns:
            True if any keyword is found in the query, False otherwise
        """
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in keywords)
