"""
Gemini API Client

Thin async wrapper around Gemini API for commentary generation.

Requires GEMINI_API_KEY environment variable.
Requires httpx: pip install httpx
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

try:
    import httpx
except ImportError:
    raise ImportError("httpx is required for the Gemini client. Install with: pip install httpx")


logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """Result from a generation call."""
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float


class GeminiClientError(Exception):
    """Base exception for Gemini client errors."""
    pass


class GeminiRateLimitError(GeminiClientError):
    """Raised when rate limited by the API."""
    pass


class GeminiAPIError(GeminiClientError):
    """Raised for API errors."""
    def __init__(self, message: str, status_code: int, response_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class GeminiClient:
    """
    Async client for Gemini API.

    Usage:
        client = GeminiClient()  # Uses GEMINI_API_KEY env var
        result = await client.generate(
            system="You are helpful.",
            user="Hello!"
        )
        print(result.text)
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    DEFAULT_MODEL = "gemini-2.0-flash-exp"  # Fast model for low latency
    FALLBACK_MODEL = "gemini-1.5-flash"     # Stable fallback

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 30.0,
    ):
        """
        Initialize the Gemini client.

        Args:
            api_key: API key. Defaults to GEMINI_API_KEY env var.
            model: Model to use. Defaults to gemini-2.0-flash-exp.
            max_retries: Maximum retry attempts for transient errors.
            retry_delay: Base delay between retries (exponential backoff).
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable not set. "
                "Get an API key from https://aistudio.google.com/app/apikey"
            )

        self.model = model or self.DEFAULT_MODEL
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

        self._client: Optional[httpx.AsyncClient] = None
        self._total_tokens_used = 0
        self._request_count = 0

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _build_url(self, model: Optional[str] = None) -> str:
        """Build the API URL for the model."""
        m = model or self.model
        return f"{self.BASE_URL}/models/{m}:generateContent?key={self.api_key}"

    def _build_request_body(
        self,
        system: str,
        user: str,
        temperature: float = 0.8,
        max_tokens: int = 256,
    ) -> dict:
        """Build the request body for the API."""
        return {
            "system_instruction": {
                "parts": [{"text": system}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": 0.95,
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ],
        }

    async def generate(
        self,
        system: str,
        user: str,
        temperature: float = 0.8,
        max_tokens: int = 256,
        model: Optional[str] = None,
    ) -> GenerationResult:
        """
        Generate a response from Gemini.

        Args:
            system: System prompt defining the assistant's role.
            user: User prompt with the specific request.
            temperature: Sampling temperature (0.0 - 1.0).
            max_tokens: Maximum tokens in response.
            model: Optional model override.

        Returns:
            GenerationResult with the generated text and metadata.

        Raises:
            GeminiRateLimitError: If rate limited after retries.
            GeminiAPIError: For other API errors.
        """
        client = await self._get_client()
        url = self._build_url(model)
        body = self._build_request_body(system, user, temperature, max_tokens)

        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                start_time = time.perf_counter()
                response = await client.post(url, json=body)
                latency_ms = (time.perf_counter() - start_time) * 1000

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_response(data, model or self.model, latency_ms)

                elif response.status_code == 429:
                    # Rate limited - exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limited, retrying in {delay:.1f}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    last_error = GeminiRateLimitError("Rate limited by Gemini API")

                elif response.status_code >= 500:
                    # Server error - retry
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Server error {response.status_code}, retrying in {delay:.1f}s")
                    await asyncio.sleep(delay)
                    last_error = GeminiAPIError(
                        f"Server error: {response.status_code}",
                        response.status_code,
                        response.text,
                    )

                else:
                    # Client error - don't retry
                    raise GeminiAPIError(
                        f"API error: {response.status_code}",
                        response.status_code,
                        response.text,
                    )

            except httpx.TimeoutException:
                delay = self.retry_delay * (2 ** attempt)
                logger.warning(f"Request timeout, retrying in {delay:.1f}s (attempt {attempt + 1})")
                await asyncio.sleep(delay)
                last_error = GeminiClientError("Request timed out")

            except httpx.RequestError as e:
                delay = self.retry_delay * (2 ** attempt)
                logger.warning(f"Request error: {e}, retrying in {delay:.1f}s")
                await asyncio.sleep(delay)
                last_error = GeminiClientError(f"Request error: {e}")

        # All retries exhausted
        if last_error:
            raise last_error
        raise GeminiClientError("Failed after all retries")

    def _parse_response(
        self,
        data: dict,
        model: str,
        latency_ms: float,
    ) -> GenerationResult:
        """Parse the API response into a GenerationResult."""
        # Extract generated text
        candidates = data.get("candidates", [])
        if not candidates:
            raise GeminiAPIError("No candidates in response", 200, str(data))

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            raise GeminiAPIError("No parts in response", 200, str(data))

        text = parts[0].get("text", "")

        # Extract token usage
        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)
        total_tokens = usage.get("totalTokenCount", prompt_tokens + completion_tokens)

        # Track usage
        self._total_tokens_used += total_tokens
        self._request_count += 1

        return GenerationResult(
            text=text,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
        )

    @property
    def total_tokens_used(self) -> int:
        """Total tokens used across all requests."""
        return self._total_tokens_used

    @property
    def request_count(self) -> int:
        """Total number of requests made."""
        return self._request_count


# Convenience function for one-off calls
async def generate_with_gemini(
    system: str,
    user: str,
    api_key: Optional[str] = None,
    model: str = GeminiClient.DEFAULT_MODEL,
    temperature: float = 0.8,
    max_tokens: int = 256,
) -> str:
    """
    One-off generation with Gemini.

    For repeated calls, use GeminiClient directly to reuse the HTTP client.

    Args:
        system: System prompt.
        user: User prompt.
        api_key: API key (defaults to GEMINI_API_KEY env var).
        model: Model to use.
        temperature: Sampling temperature.
        max_tokens: Maximum response tokens.

    Returns:
        Generated text.
    """
    async with GeminiClient(api_key=api_key, model=model) as client:
        result = await client.generate(
            system=system,
            user=user,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return result.text
