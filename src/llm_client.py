"""LLM Client with Gemini multi-model fallback and OpenAI support."""
import logging
import json
import time
from typing import List, Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from src.conversation import LLMResponse

logger = logging.getLogger("llm_chatbot")

# Ordered list of Gemini models to try — each has its own separate quota pool.
GEMINI_MODEL_CHAIN = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]

# Cooldown in seconds before retrying a rate-limited model (free tier = ~60s window)
RATE_LIMIT_COOLDOWN = 62

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# Module-level cooldown tracker: model -> timestamp when it can be used again
_model_cooldown: Dict[str, float] = {}


def _call_gemini(api_key: str, model: str, messages: List[Dict[str, str]], temperature: float) -> LLMResponse:
    """Single REST call to a specific Gemini model."""
    try:
        system_instruction = None
        contents = []

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
            elif msg["role"] == "assistant":
                contents.append({"role": "model", "parts": [{"text": msg["content"]}]})

        body: Dict = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        url = f"{BASE_URL}/{model}:generateContent?key={api_key}"
        data = json.dumps(body).encode("utf-8")
        req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

        with urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        text = (
            result.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        return LLMResponse(success=True, content=text, error_message=None, token_count=None)

    except HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        return _classify_error(f"HTTP {e.code}: {body_text}")
    except URLError as e:
        return _classify_error(f"Connection error: {e.reason}")
    except Exception as error:
        return _classify_error(str(error))


def _classify_error(error_str: str) -> LLMResponse:
    """Classify an error string into a structured LLMResponse."""
    err_lower = error_str.lower()
    if "429" in err_lower or "quota" in err_lower or "rate" in err_lower or "resource_exhausted" in err_lower:
        msg = "rate_limit"
    elif "503" in err_lower or "unavailable" in err_lower or "overloaded" in err_lower or "high demand" in err_lower:
        msg = "transient"
    elif "403" in err_lower or "api key" in err_lower or "authentication" in err_lower:
        msg = "auth"
    elif "timeout" in err_lower:
        msg = "timeout"
    else:
        msg = f"error:{error_str[:200]}"

    return LLMResponse(success=False, content="", error_message=msg, token_count=None)


class GeminiClient:
    """Gemini client that walks through a model chain on rate-limit errors.

    On rate limit (429): tries the next model in GEMINI_MODEL_CHAIN.
    On transient error (503): retries the same model up to 3 times with backoff.
    All models share the same API key but have independent quota pools.
    """

    def __init__(self, api_key: str, model: str, temperature: float):
        self.api_key = api_key
        self.temperature = temperature
        # Build chain: requested model first, then the rest
        chain = [model] + [m for m in GEMINI_MODEL_CHAIN if m != model]
        self.model_chain = chain

    def generate_response(self, messages: List[Dict[str, str]]) -> LLMResponse:
        last_error: Optional[LLMResponse] = None
        now = time.time()

        for model in self.model_chain:
            # Skip models still in cooldown
            ready_at = _model_cooldown.get(model, 0)
            if now < ready_at:
                remaining = int(ready_at - now)
                logger.info(f"Model {model} in cooldown for {remaining}s more, skipping...")
                last_error = LLMResponse(
                    success=False, content="", error_message="rate_limit", token_count=None
                )
                continue

            result = self._try_with_retries(model, messages)
            if result.success:
                if model != self.model_chain[0]:
                    logger.info(f"Succeeded with fallback model: {model}")
                return result

            err = result.error_message or ""
            if err == "rate_limit":
                # Put this model in cooldown and try the next one
                _model_cooldown[model] = time.time() + RATE_LIMIT_COOLDOWN
                logger.warning(f"Rate limit on {model}, cooling down for {RATE_LIMIT_COOLDOWN}s, trying next model...")
                last_error = result
                continue
            else:
                last_error = result
                break

        return LLMResponse(
            success=False,
            content="",
            error_message=self._friendly_error(last_error),
            token_count=None,
        )

    def _try_with_retries(self, model: str, messages: List[Dict[str, str]]) -> LLMResponse:
        """Try a single model up to 3 times for transient errors."""
        last: Optional[LLMResponse] = None
        for attempt in range(3):
            result = _call_gemini(self.api_key, model, messages, self.temperature)
            if result.success:
                return result
            last = result
            err = result.error_message or ""
            if err == "transient":
                wait = 2 ** attempt
                logger.info(f"Transient error on {model}, retrying in {wait}s (attempt {attempt + 1}/3)...")
                time.sleep(wait)
            else:
                return result  # rate_limit / auth / other — stop retrying this model
        return last  # type: ignore

    @staticmethod
    def _friendly_error(response: Optional[LLMResponse]) -> str:
        err = (response.error_message or "") if response else ""
        if err == "rate_limit":
            return "The AI service is currently busy. Please wait a moment and try again."
        if err == "transient":
            return "The AI service is temporarily unavailable. Please try again shortly."
        if err == "auth":
            return "API authentication failed. Please check your API key configuration."
        if err == "timeout":
            return "The request timed out. Please try again."
        if err.startswith("error:"):
            return f"An error occurred: {err[6:]}"
        return "Unable to get a response right now. Please try again."


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
                timeout=self.timeout,
            )
            content = response.choices[0].message.content
            token_count = response.usage.total_tokens if response.usage else None
            return LLMResponse(success=True, content=content, error_message=None, token_count=token_count)
        except Exception as error:
            return self._handle_error(error)

    def _handle_error(self, error: Exception) -> LLMResponse:
        try:
            from openai import AuthenticationError, RateLimitError, APITimeoutError, APIConnectionError
            if isinstance(error, AuthenticationError):
                msg = "OpenAI authentication failed"
            elif isinstance(error, RateLimitError):
                msg = "OpenAI rate limit exceeded"
            elif isinstance(error, APITimeoutError):
                msg = "OpenAI request timed out"
            elif isinstance(error, APIConnectionError):
                msg = "OpenAI connection failed"
            else:
                msg = f"OpenAI error: {str(error)}"
        except ImportError:
            msg = f"OpenAI error: {str(error)}"
        return LLMResponse(success=False, content="", error_message=msg, token_count=None)


class LLMClient:
    """Unified LLM client — Gemini (multi-model chain) with optional OpenAI fallback."""

    def __init__(self, api_key: str, model: str, timeout: int, temperature: float,
                 provider: str = "gemini",
                 gemini_api_key: str = "",
                 openai_api_key: str = ""):
        self.primary = None
        self.openai_fallback = None

        if provider == "gemini" and gemini_api_key:
            self.primary = GeminiClient(gemini_api_key, model, temperature)
            if openai_api_key:
                self.openai_fallback = self._try_create_openai(openai_api_key, "gpt-3.5-turbo", timeout, temperature)
        elif provider == "openai" and openai_api_key:
            self.openai_fallback = self._try_create_openai(openai_api_key, model, timeout, temperature)
            if gemini_api_key:
                self.primary = GeminiClient(gemini_api_key, "gemini-2.5-flash", temperature)
        else:
            if gemini_api_key:
                self.primary = GeminiClient(gemini_api_key, model or "gemini-2.5-flash", temperature)
            if openai_api_key:
                client = self._try_create_openai(openai_api_key, model or "gpt-3.5-turbo", timeout, temperature)
                if self.primary is None:
                    self.openai_fallback = client
                elif client:
                    self.openai_fallback = client

    @staticmethod
    def _try_create_openai(api_key, model, timeout, temperature):
        try:
            return OpenAIClient(api_key, model, timeout, temperature)
        except ImportError:
            logger.warning("openai package not installed, OpenAI fallback unavailable")
            return None

    def generate_response(self, messages: List[Dict[str, str]]) -> LLMResponse:
        if self.primary is None and self.openai_fallback is None:
            return LLMResponse(
                success=False, content="",
                error_message="No LLM provider configured. Check your API keys.",
                token_count=None,
            )

        # Try Gemini (with its internal model chain)
        if self.primary:
            response = self.primary.generate_response(messages)
            if response.success:
                return response
            logger.warning(f"Gemini chain exhausted: {response.error_message}")

            # Try OpenAI as last resort
            if self.openai_fallback:
                logger.info("Attempting OpenAI fallback...")
                oai_response = self.openai_fallback.generate_response(messages)
                if oai_response.success:
                    return oai_response
                logger.warning(f"OpenAI fallback also failed: {oai_response.error_message}")

            return response  # Return Gemini's friendly error message

        # OpenAI-only mode
        return self.openai_fallback.generate_response(messages)
