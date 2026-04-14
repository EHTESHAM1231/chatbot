"""LLM Client with Gemini primary and OpenAI fallback support."""
import logging
from typing import List, Dict
from src.conversation import LLMResponse

logger = logging.getLogger("llm_chatbot")


class GeminiClient:
    """Client for Google Gemini API using the new google.genai SDK."""

    def __init__(self, api_key: str, model: str, temperature: float):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model_name = model
        self.temperature = temperature

    def generate_response(self, messages: List[Dict[str, str]]) -> LLMResponse:
        """Generate a response using Gemini API.

        Converts OpenAI-style messages to Gemini format and calls the API.
        Retries up to 2 times on transient errors (503, etc.).
        """
        import time

        last_error = None
        for attempt in range(3):
            result = self._try_generate(messages)
            if result.success:
                return result
            last_error = result
            # Only retry on transient errors
            err = (result.error_message or "").lower()
            if "503" in err or "unavailable" in err or "overloaded" in err or "high demand" in err:
                wait = 2 ** attempt
                logger.info(f"Gemini transient error, retrying in {wait}s (attempt {attempt + 1}/3)...")
                time.sleep(wait)
            else:
                return result
        return last_error

    def _try_generate(self, messages: List[Dict[str, str]]) -> LLMResponse:
        """Single attempt to generate a response."""
        try:
            from google.genai import types

            # Extract system instruction and build contents
            system_instruction = None
            contents = []

            for msg in messages:
                if msg["role"] == "system":
                    system_instruction = msg["content"]
                elif msg["role"] == "user":
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part(text=msg["content"])]
                    ))
                elif msg["role"] == "assistant":
                    contents.append(types.Content(
                        role="model",
                        parts=[types.Part(text=msg["content"])]
                    ))

            config = types.GenerateContentConfig(
                temperature=self.temperature,
            )
            if system_instruction:
                config.system_instruction = system_instruction

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )

            return LLMResponse(
                success=True,
                content=response.text or "",
                error_message=None,
                token_count=None
            )

        except Exception as error:
            return self._handle_error(error)

    def _handle_error(self, error: Exception) -> LLMResponse:
        error_str = str(error).lower()
        if "quota" in error_str or "rate" in error_str or "429" in error_str:
            error_message = "Gemini rate limit exceeded"
        elif "api key" in error_str or "authentication" in error_str or "403" in error_str:
            error_message = "Gemini authentication failed: Invalid API key"
        elif "timeout" in error_str:
            error_message = "Gemini request timed out"
        else:
            error_message = f"Gemini API error: {str(error)}"

        return LLMResponse(
            success=False,
            content="",
            error_message=error_message,
            token_count=None
        )


class OpenAIClient:
    """Client for OpenAI API."""

    def __init__(self, api_key: str, model: str, timeout: int, temperature: float):
        from openai import OpenAI
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.client = OpenAI(api_key=api_key, timeout=timeout)

    def generate_response(self, messages: List[Dict[str, str]]) -> LLMResponse:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                timeout=self.timeout
            )
            content = response.choices[0].message.content
            token_count = response.usage.total_tokens if response.usage else None

            return LLMResponse(
                success=True,
                content=content,
                error_message=None,
                token_count=token_count
            )
        except Exception as error:
            return self._handle_error(error)

    def _handle_error(self, error: Exception) -> LLMResponse:
        from openai import AuthenticationError, RateLimitError, APITimeoutError, APIConnectionError

        if isinstance(error, AuthenticationError):
            error_message = "OpenAI authentication failed: Invalid API key"
        elif isinstance(error, RateLimitError):
            error_message = "OpenAI rate limit exceeded"
        elif isinstance(error, APITimeoutError):
            error_message = "OpenAI request timed out"
        elif isinstance(error, APIConnectionError):
            error_message = "OpenAI connection failed"
        else:
            error_message = f"OpenAI API error: {str(error)}"

        return LLMResponse(
            success=False,
            content="",
            error_message=error_message,
            token_count=None
        )


class LLMClient:
    """Unified LLM client with primary provider and automatic fallback.

    Uses the configured primary provider (Gemini or OpenAI) and falls back
    to the other if the primary fails.
    """

    def __init__(self, api_key: str, model: str, timeout: int, temperature: float,
                 provider: str = "gemini",
                 gemini_api_key: str = "",
                 openai_api_key: str = ""):
        self.provider = provider
        self.primary = None
        self.fallback = None

        # Initialize primary client
        if provider == "gemini" and gemini_api_key:
            self.primary = GeminiClient(gemini_api_key, model, temperature)
            if openai_api_key:
                self.fallback = self._try_create_openai(openai_api_key, "gpt-3.5-turbo", timeout, temperature)
        elif provider == "openai" and openai_api_key:
            self.primary = self._try_create_openai(openai_api_key, model, timeout, temperature)
            if gemini_api_key:
                self.fallback = GeminiClient(gemini_api_key, "gemini-2.5-flash", temperature)
        else:
            if gemini_api_key:
                self.primary = GeminiClient(gemini_api_key, model or "gemini-2.5-flash", temperature)
            if openai_api_key:
                client = self._try_create_openai(openai_api_key, model or "gpt-3.5-turbo", timeout, temperature)
                if self.primary is None:
                    self.primary = client
                elif client:
                    self.fallback = client

    @staticmethod
    def _try_create_openai(api_key, model, timeout, temperature):
        """Try to create OpenAI client, return None if openai package not installed."""
        try:
            return OpenAIClient(api_key, model, timeout, temperature)
        except ImportError:
            logger.warning("openai package not installed, OpenAI fallback unavailable")
            return None

    def generate_response(self, messages: List[Dict[str, str]]) -> LLMResponse:
        """Generate a response, falling back to secondary provider on failure."""
        if self.primary is None:
            return LLMResponse(
                success=False,
                content="",
                error_message="No LLM provider configured. Check your API keys.",
                token_count=None
            )

        # Try primary
        response = self.primary.generate_response(messages)
        if response.success:
            return response

        primary_error = response.error_message
        logger.warning(f"Primary provider failed: {primary_error}")

        # Try fallback
        if self.fallback:
            logger.info("Attempting fallback provider...")
            fallback_response = self.fallback.generate_response(messages)
            if fallback_response.success:
                return fallback_response
            logger.warning(f"Fallback provider also failed: {fallback_response.error_message}")
            return LLMResponse(
                success=False,
                content="",
                error_message=f"All providers failed. Primary: {primary_error}. Fallback: {fallback_response.error_message}",
                token_count=None
            )

        return response
