"""
Production OpenAI API client with real HTTP implementation.
Includes retry logic, timeout handling, and rate limiting.
"""

import time
import json
from typing import Any, Dict, Optional, List
import urllib.request
import urllib.error
import logging

logger = logging.getLogger(__name__)


class OpenAIError(Exception):
    """Base exception for OpenAI API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class RateLimitError(OpenAIError):
    """Raised when rate limit is exceeded."""
    pass


class TimeoutError(OpenAIError):
    """Raised when request times out."""
    pass


class InvalidRequestError(OpenAIError):
    """Raised when request parameters are invalid."""
    pass


class OpenAI:
    """
    Production implementation of OpenAI API client.

    Features:
    - Real HTTP requests with proper error handling
    - Automatic retry with exponential backoff
    - Rate limiting protection
    - Timeout handling
    - Request/response validation
    """

    BASE_URL = "https://api.openai.com/v1/"
    DEFAULT_TIMEOUT = 30  # seconds
    MAX_RETRIES = 3

    def __init__(
        self,
        api_key: str,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
        organization: Optional[str] = None
    ):
        """
        Initialize the OpenAI client.

        Args:
            api_key: OpenAI API key
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            organization: Optional organization ID
        """
        if not api_key or not isinstance(api_key, str):
            raise ValueError("Valid API key is required")

        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.organization = organization
        self.last_request_time = 0.0
        self.min_request_interval = 0.1  # Minimum 100ms between requests

    def _make_request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make HTTP request to OpenAI API with retry logic.

        Args:
            endpoint: API endpoint path
            method: HTTP method (GET, POST, etc.)
            data: Request payload
            retry_count: Current retry attempt number

        Returns:
            Response data as dictionary

        Raises:
            OpenAIError: On API errors
            TimeoutError: On timeout
            RateLimitError: On rate limit exceeded
        """
        # Rate limiting: ensure minimum interval between requests
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)

        self.last_request_time = time.time()

        url = f"{self.BASE_URL}{endpoint}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if self.organization:
            headers["OpenAI-Organization"] = self.organization

        try:
            # Prepare request
            request_data = json.dumps(data).encode('utf-8') if data else None
            req = urllib.request.Request(
                url,
                data=request_data,
                headers=headers,
                method=method
            )

            # Make request with timeout
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                response_body = response.read().decode('utf-8')
                return json.loads(response_body)

        except urllib.error.HTTPError as e:
            status_code = e.code
            try:
                response_body = e.read().decode('utf-8')
                error_data = json.loads(response_body)
                error_message = error_data.get("error", {}).get("message", str(e.reason))
            except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as parse_err:
                logger.debug("Failed to parse error response: %s", parse_err)
                response_body = ""
                error_message = str(e.reason)

            # Handle rate limiting
            if status_code == 429:
                if retry_count < self.max_retries:
                    # Exponential backoff
                    wait_time = (2 ** retry_count) * 1.0
                    logger.warning("Rate limited. Retrying in %.1fs...", wait_time, extra={"retry_count": retry_count})
                    time.sleep(wait_time)
                    return self._make_request(endpoint, method, data, retry_count + 1)
                else:
                    raise RateLimitError(
                        "Rate limit exceeded and max retries reached",
                        status_code=status_code,
                        response_body=response_body
                    )

            # Handle invalid requests
            elif status_code == 400:
                raise InvalidRequestError(
                    f"Invalid request: {error_message}",
                    status_code=status_code,
                    response_body=response_body
                )

            # Handle authentication errors
            elif status_code == 401:
                raise OpenAIError(
                    "Authentication failed. Check your API key.",
                    status_code=status_code,
                    response_body=response_body
                )

            # Handle server errors with retry
            elif status_code >= 500 and retry_count < self.max_retries:
                wait_time = (2 ** retry_count) * 0.5
                logger.warning("Server error %d. Retrying in %.1fs...", status_code, wait_time, extra={"retry_count": retry_count})
                time.sleep(wait_time)
                return self._make_request(endpoint, method, data, retry_count + 1)

            # Other HTTP errors
            else:
                raise OpenAIError(
                    f"API request failed: {error_message}",
                    status_code=status_code,
                    response_body=response_body
                )

        except urllib.error.URLError as e:
            if "timed out" in str(e.reason).lower():
                if retry_count < self.max_retries:
                    wait_time = (2 ** retry_count) * 0.5
                    logger.warning("Request timeout. Retrying in %.1fs...", wait_time, extra={"retry_count": retry_count})
                    time.sleep(wait_time)
                    return self._make_request(endpoint, method, data, retry_count + 1)
                else:
                    raise TimeoutError(
                        f"Request timed out after {self.timeout}s and max retries reached"
                    )
            else:
                raise OpenAIError(f"Network error: {e.reason}")

        except json.JSONDecodeError as e:
            raise OpenAIError(f"Failed to parse API response: {e}")

        except (TypeError, ValueError, OverflowError) as e:
            raise OpenAIError(f"Unexpected error during API request: {e}")

    def ChatCompletion(
        self,
        model: str = "gpt-3.5-turbo",
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> Any:
        """
        Create a chat completion.

        Args:
            model: Model to use (e.g., "gpt-3.5-turbo", "gpt-4")
            messages: List of message objects with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            Response object with choices, usage, etc.

        Raises:
            ValueError: If required parameters are missing
            OpenAIError: On API errors
        """
        if messages is None:
            raise ValueError("'messages' parameter is required")

        # Build request data
        request_data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens is not None:
            request_data["max_tokens"] = max_tokens

        # Add any additional parameters
        request_data.update(kwargs)

        # Make API request
        response_dict = self._make_request("chat/completions", method="POST", data=request_data)

        # Create response object with attribute access
        return ChatCompletionResponse(response_dict)

    def Completion(
        self,
        model: str = "gpt-3.5-turbo-instruct",
        prompt: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: int = 16,
        **kwargs: Any
    ) -> Any:
        """
        Create a text completion (legacy endpoint).

        Args:
            model: Model to use
            prompt: Text prompt
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            Response object

        Raises:
            ValueError: If required parameters are missing
            OpenAIError: On API errors
        """
        if prompt is None:
            raise ValueError("'prompt' parameter is required")

        request_data = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        request_data.update(kwargs)

        response_dict = self._make_request("completions", method="POST", data=request_data)

        return CompletionResponse(response_dict)


class ChatCompletionResponse:
    """Wrapper for chat completion response with attribute access."""

    def __init__(self, data: Dict[str, Any]):
        self._data = data
        self.choices = data.get("choices", [])
        self.usage = data.get("usage", {})
        self.id = data.get("id", "")
        self.model = data.get("model", "")
        self.created = data.get("created", 0)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)


class CompletionResponse:
    """Wrapper for completion response with attribute access."""

    def __init__(self, data: Dict[str, Any]):
        self._data = data
        self.choices = data.get("choices", [])
        self.usage = data.get("usage", {})
        self.id = data.get("id", "")
        self.model = data.get("model", "")
        self.created = data.get("created", 0)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
