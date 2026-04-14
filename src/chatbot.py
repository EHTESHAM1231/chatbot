"""
Main chatbot orchestrator for LLM Chatbot.

This module integrates all components (router, prompt engine, LLM client,
formatter, conversation store, logger) into a unified chatbot interface.
"""

import logging
from src.config import Config
from src.router import IntentRouter
from src.prompts import PromptEngine
from src.llm_client import LLMClient
from src.formatter import ResponseFormatter
from src.conversation import ConversationStore
from src.logger import setup_logger, log_query, log_response, log_error


class Chatbot:
    """Main chatbot orchestrator integrating all system components.
    
    The Chatbot class coordinates the complete query processing pipeline:
    1. Input validation
    2. Intent classification
    3. Prompt construction with context
    4. LLM API invocation
    5. Response formatting
    6. Conversation storage
    
    All operations are wrapped in error handling with comprehensive logging.
    """
    
    def __init__(self, config: Config):
        """Initialize chatbot with all components.
        
        Args:
            config: Configuration object with API credentials and settings
        """
        # Initialize logger
        self.logger = setup_logger(config.log_level)
        self.logger.info("Initializing chatbot components...")
        
        # Initialize conversation store
        self.conversation_store = ConversationStore(max_exchanges=3)
        
        # Initialize components
        self.router = IntentRouter()
        self.prompt_engine = PromptEngine(self.conversation_store)
        self.llm_client = LLMClient(
            api_key=config.api_key,
            model=config.model,
            timeout=config.timeout,
            temperature=config.temperature,
            provider=config.provider,
            gemini_api_key=config.gemini_api_key,
            openai_api_key=config.openai_api_key
        )
        self.formatter = ResponseFormatter()
        
        self.logger.info("Chatbot initialized successfully")
    
    def process_query(self, query: str) -> str:
        """Process user query through complete pipeline.
        
        Main orchestration function that coordinates all components:
        - Validates input
        - Classifies intent
        - Builds structured prompt
        - Calls LLM API
        - Formats response
        - Stores conversation
        
        Args:
            query: User input text
            
        Returns:
            Formatted response string or error message
        """
        try:
            # Validate input
            if not query.strip():
                return "Please provide a valid query."
            
            # Classify intent
            intent = self.router.classify_intent(query)
            log_query(self.logger, query, intent.value)
            
            # Build prompt with context
            messages = self.prompt_engine.build_prompt(intent, query)
            
            # Call LLM API
            response = self.llm_client.generate_response(messages)
            
            # Handle API errors
            if not response.success:
                log_error(self.logger, Exception(response.error_message))
                return response.error_message
            
            # Format response
            formatted = self.formatter.format_response(response.content, intent)
            
            # Log successful response
            log_response(self.logger, formatted, response.token_count)
            
            # Store conversation
            self.conversation_store.add_message("user", query)
            self.conversation_store.add_message("assistant", formatted)
            
            return formatted
            
        except Exception as e:
            log_error(self.logger, e)
            return "An unexpected error occurred. Please try again."
