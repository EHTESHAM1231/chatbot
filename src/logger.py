"""
Logging system for the LLM Chatbot.

This module provides structured logging functionality with console and file handlers.
Implements Requirements 10.1, 10.2, 10.3, 10.4, 10.5.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logger(log_level: str = "INFO") -> logging.Logger:
    """
    Set up and configure the logger with console and file handlers.
    
    Args:
        log_level: Logging level (DEBUG, INFO, ERROR). Defaults to INFO.
        
    Returns:
        Configured logger instance.
        
    Requirements:
        - 10.4: Write logs to file in logs directory
        - 10.5: Support configurable log levels
    """
    # Create logger
    logger = logging.getLogger("llm_chatbot")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Prevent duplicate handlers if logger already configured
    if logger.handlers:
        return logger
    
    # Define log format
    log_format = "[%(asctime)s] %(levelname)s - %(name)s - %(message)s"
    formatter = logging.Formatter(log_format)
    
    # Console handler - all levels
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler - INFO and above
    # Ensure logs directory exists
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    log_file = logs_dir / "chatbot.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def log_query(logger: logging.Logger, query: str, intent: str) -> None:
    """
    Log a user query with timestamp and classified intent.
    
    Args:
        logger: Logger instance.
        query: User query text.
        intent: Classified intent (summarization, qa, chat).
        
    Requirements:
        - 10.1: Log each query with timestamp and classified intent
    """
    timestamp = datetime.now().isoformat()
    logger.info(f"Query received | Intent: {intent} | Timestamp: {timestamp} | Query: {query[:100]}")


def log_response(logger: logging.Logger, response: str, token_count: Optional[int] = None) -> None:
    """
    Log an LLM response with timestamp and token count.
    
    Args:
        logger: Logger instance.
        response: LLM response text.
        token_count: Number of tokens used (optional).
        
    Requirements:
        - 10.2: Log each LLM response with timestamp and token count
    """
    timestamp = datetime.now().isoformat()
    tokens_info = f"Tokens: {token_count}" if token_count else "Tokens: N/A"
    logger.info(f"Response generated | Timestamp: {timestamp} | {tokens_info} | Response: {response[:100]}")


def log_error(logger: logging.Logger, error: Exception) -> None:
    """
    Log an error with full error details and stack trace.
    
    Args:
        logger: Logger instance.
        error: Exception object.
        
    Requirements:
        - 10.3: Log errors with full error details and stack traces
    """
    logger.error(f"Error occurred: {type(error).__name__}: {str(error)}", exc_info=True)
