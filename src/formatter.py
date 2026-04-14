"""
Response formatting module for LLM Chatbot.

This module provides intent-specific formatting for LLM responses:
- Summarization: Bullet points and section headers
- Question Answering: Highlighted answers with supporting details
- General Chat: Natural conversational flow
"""

import re
from src.conversation import Intent


class ResponseFormatter:
    """Formats LLM responses based on intent type."""
    
    def format_response(self, content: str, intent: Intent) -> str:
        """Format response content based on intent.
        
        Args:
            content: Raw response content from LLM
            intent: Query intent type
            
        Returns:
            Formatted response string
        """
        if intent == Intent.SUMMARIZATION:
            return self._format_summarization(content)
        elif intent == Intent.QUESTION_ANSWERING:
            return self._format_qa(content)
        elif intent == Intent.GENERAL_CHAT:
            return self._format_chat(content)
        else:
            # Fallback to chat formatting
            return self._format_chat(content)
    
    def _format_summarization(self, content: str) -> str:
        """Format summarization responses with bullet points and structure.
        
        Args:
            content: Raw summarization content
            
        Returns:
            Formatted content with bullet points and section headers
        """
        # Normalize whitespace first
        content = self._normalize_whitespace(content)
        
        # Ensure bullet points are properly formatted
        # Convert various bullet formats to consistent format
        content = re.sub(r'^[\*\-\+]\s+', '• ', content, flags=re.MULTILINE)
        
        # Add spacing after section headers (lines ending with :)
        content = re.sub(r'([^\n]):(\n)', r'\1:\2\n', content)
        
        return content.strip()
    
    def _format_qa(self, content: str) -> str:
        """Format QA responses with highlighted answer and supporting details.
        
        Args:
            content: Raw QA content
            
        Returns:
            Formatted content with structured answer presentation
        """
        # Normalize whitespace first
        content = self._normalize_whitespace(content)
        
        # If content has multiple paragraphs, assume first is the direct answer
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        if len(paragraphs) > 1:
            # Highlight the direct answer
            answer = paragraphs[0]
            details = '\n\n'.join(paragraphs[1:])
            
            # Format with clear separation
            formatted = f"**Answer:**\n{answer}\n\n**Details:**\n{details}"
            return formatted
        
        # Single paragraph - return as is
        return content.strip()
    
    def _format_chat(self, content: str) -> str:
        """Format general chat responses preserving conversational flow.
        
        Args:
            content: Raw chat content
            
        Returns:
            Formatted content with natural conversational structure
        """
        # Normalize whitespace while preserving paragraph structure
        content = self._normalize_whitespace(content)
        
        return content.strip()
    
    def _normalize_whitespace(self, text: str) -> str:
        """Remove excessive whitespace and normalize line breaks.
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text with cleaned whitespace
        """
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        
        # Join lines back together
        text = '\n'.join(lines)
        
        # Replace multiple consecutive newlines with max 2
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove excessive spaces (multiple spaces to single space)
        text = re.sub(r' {2,}', ' ', text)
        
        return text
