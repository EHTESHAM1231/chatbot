"""
Prompt engineering module for LLM Chatbot.

This module provides structured prompt construction with intent-specific
system prompts and conversation context formatting.
"""

from typing import List, Dict
from src.conversation import ConversationStore, Intent, Message


class PromptEngine:
    """Constructs structured prompts with role definitions and context.
    
    The PromptEngine builds prompts in OpenAI Chat Completion format,
    including system prompts tailored to the query intent and conversation
    context from recent exchanges.
    """
    
    def __init__(self, conversation_store: ConversationStore):
        """Initialize prompt engine.
        
        Args:
            conversation_store: Store for retrieving conversation context
        """
        self.conversation_store = conversation_store
    
    def build_prompt(self, intent: Intent, query: str) -> List[Dict[str, str]]:
        """Construct full prompt with system message, context, and query.
        
        Args:
            intent: Classified intent for the query
            query: Current user query
            
        Returns:
            List of message dictionaries in OpenAI format:
            [
                {"role": "system", "content": "<system_prompt>"},
                {"role": "user", "content": "<previous_message>"},
                {"role": "assistant", "content": "<previous_response>"},
                ...
                {"role": "user", "content": "<current_query>"}
            ]
        """
        # Start with system prompt
        messages = [
            {"role": "system", "content": self._get_system_prompt(intent)}
        ]
        
        # Add conversation context
        context_messages = self._format_context(
            self.conversation_store.get_recent_messages()
        )
        messages.extend(context_messages)
        
        # Add current query
        messages.append({"role": "user", "content": query})
        
        return messages
    
    def _get_system_prompt(self, intent: Intent) -> str:
        """Return intent-specific system prompt.
        
        Args:
            intent: Query intent type
            
        Returns:
            System prompt string with role definition and task instructions
        """
        prompts = {
            Intent.SUMMARIZATION: (
                "You are a professional summarization assistant. Your task is to extract key points "
                "and present them as concise bullet points. Focus on main ideas, important details, "
                "and actionable insights. Format your response as a bulleted list."
            ),
            Intent.QUESTION_ANSWERING: (
                "You are a knowledgeable assistant specializing in answering questions clearly and "
                "accurately. Provide direct answers followed by supporting details. Structure your "
                "response with the answer first, then explanation."
            ),
            Intent.GENERAL_CHAT: (
                "You are a helpful, friendly conversational assistant. Engage naturally with the user, "
                "provide thoughtful responses, and maintain context from previous messages."
            )
        }
        
        return prompts.get(intent, prompts[Intent.GENERAL_CHAT])
    
    def _format_context(self, messages: List[Message]) -> List[Dict[str, str]]:
        """Convert Message objects to OpenAI format.
        
        Args:
            messages: List of Message objects from conversation history
            
        Returns:
            List of message dictionaries in OpenAI format:
            [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
        """
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
