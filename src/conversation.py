"""
Conversation management module for LLM Chatbot.

This module provides data models and conversation storage functionality:
- Message: Represents a single conversation message
- Intent: Enumeration of supported query intents
- LLMResponse: Encapsulates LLM API response
- ConversationStore: Maintains conversation history with sliding window
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional


class Intent(Enum):
    """Supported query intent types."""
    SUMMARIZATION = "summarization"
    QUESTION_ANSWERING = "qa"
    GENERAL_CHAT = "chat"


@dataclass
class Message:
    """Represents a single conversation message.
    
    Attributes:
        role: Message role ("user" or "assistant")
        content: Message text content
        timestamp: When the message was created
    """
    role: str
    content: str
    timestamp: datetime


@dataclass
class LLMResponse:
    """Encapsulates LLM API response with metadata.
    
    Attributes:
        success: Whether the API call succeeded
        content: Response text content
        error_message: Error description if success is False
        token_count: Number of tokens used (if available)
    """
    success: bool
    content: str
    error_message: Optional[str] = None
    token_count: Optional[int] = None


class ConversationStore:
    """Maintains conversation history with fixed-size sliding window.
    
    Stores the last N exchanges (user + assistant message pairs) in memory.
    Uses FIFO eviction when the limit is exceeded.
    """
    
    def __init__(self, max_exchanges: int = 3):
        """Initialize conversation store.
        
        Args:
            max_exchanges: Maximum number of exchanges to maintain (default: 3)
        """
        self.max_exchanges = max_exchanges
        self._messages: List[Message] = []
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history.
        
        Args:
            role: Message role ("user" or "assistant")
            content: Message text content
        """
        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now()
        )
        self._messages.append(message)
        self._maintain_window_size()
    
    def get_recent_messages(self) -> List[Message]:
        """Get recent messages within the window size.
        
        Returns:
            List of recent messages in chronological order
        """
        return self._messages.copy()
    
    def clear_history(self) -> None:
        """Clear all conversation history."""
        self._messages.clear()
    
    def _maintain_window_size(self) -> None:
        """Enforce FIFO eviction to maintain window size.
        
        Removes oldest messages when total exceeds max_exchanges * 2
        (since each exchange consists of user + assistant messages).
        """
        max_messages = self.max_exchanges * 2
        if len(self._messages) > max_messages:
            # Remove oldest messages to maintain window size
            self._messages = self._messages[-max_messages:]
