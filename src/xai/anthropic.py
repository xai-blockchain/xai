"""
Production Anthropic API client with real HTTP implementation.
Includes retry logic, timeout handling, and rate limiting.
"""

import time
import json
from typing import Any, Dict, Optional
import urllib.request
import urllib.error
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Exception raised for API-related errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class RateLimitError(APIError):
    """Raised when rate limit is exceeded."""
    pass


class TimeoutError(APIError):
    """Raised when request times out."""
    pass


class Anthropic:
    """
    Production implementation of Anthropic API client.

    Features:
    - Real HTTP requests with proper error handling
    - Automatic retry with exponential backoff
    - Rate limiting protection
    - Timeout handling
    - Request/response validation
    """

    BASE_URL = "https://api.anthropic.com/v1/"
    DEFAULT_TIMEOUT = 30  # seconds
    MAX_RETRIES = 3

    def __init__(
        self,
        api_key: str,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES
    ) -> None:
        """
        Initialize the Anthropic client.

        Args:
            api_key: API authentication key
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        if not api_key or not isinstance(api_key, str):
            raise ValueError("Valid API key is required")

        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
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
        Make HTTP request to Anthropic API with retry logic.

        Args:
            endpoint: API endpoint path
            method: HTTP method (GET, POST, etc.)
            data: Request payload
            retry_count: Current retry attempt number

        Returns:
            Response data as dictionary

        Raises:
            APIError: On API errors
            TimeoutError: On timeout
            RateLimitError: On rate limit exceeded
        """
        # Rate limiting: ensure minimum interval between requests
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)

        self.last_request_time = time.time()

        url = urljoin(self.BASE_URL, endpoint)

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

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
            response_body = e.read().decode('utf-8') if e.fp else ""

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

            # Handle server errors with retry
            elif status_code >= 500 and retry_count < self.max_retries:
                wait_time = (2 ** retry_count) * 0.5
                logger.warning("Server error %d. Retrying in %.1fs...", status_code, wait_time, extra={"retry_count": retry_count})
                time.sleep(wait_time)
                return self._make_request(endpoint, method, data, retry_count + 1)

            # Other HTTP errors
            else:
                raise APIError(
                    f"API request failed: {e.reason}",
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
                raise APIError(f"Network error: {e.reason}")

        except json.JSONDecodeError as e:
            raise APIError(f"Failed to parse API response: {e}")

        except Exception as e:
            raise APIError(f"Unexpected error during API request: {e}")

    def completion(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Create a completion request to Anthropic API.

        Args:
            **kwargs: Completion parameters including:
                - model (str): Model to use (e.g., "claude-2", "claude-instant-1")
                - prompt (str): Input prompt
                - max_tokens_to_sample (int): Maximum tokens in response
                - temperature (float): Sampling temperature (0-1)
                - Additional parameters as per Anthropic API docs

        Returns:
            Dictionary containing completion response with:
                - completion: Generated text
                - id: Request ID
                - model: Model used
                - stop_reason: Why generation stopped

        Raises:
            ValueError: If required parameters are missing
            APIError: On API errors
        """
        # Validate required parameters
        if "prompt" not in kwargs:
            raise ValueError("'prompt' is required for completion")
        if "model" not in kwargs:
            kwargs["model"] = "claude-2"
        if "max_tokens_to_sample" not in kwargs:
            kwargs["max_tokens_to_sample"] = 1024

        # Make API request
        response = self._make_request("complete", method="POST", data=kwargs)

        return response

    def messages(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Create a messages request to Anthropic API (newer API format).

        Args:
            **kwargs: Message parameters including:
                - model (str): Model to use
                - messages (list): List of message objects
                - max_tokens (int): Maximum tokens in response
                - Additional parameters as per Anthropic API docs

        Returns:
            Dictionary containing message response

        Raises:
            ValueError: If required parameters are missing
            APIError: On API errors
        """
        # Validate required parameters
        if "messages" not in kwargs:
            raise ValueError("'messages' is required")
        if "model" not in kwargs:
            kwargs["model"] = "claude-2"
        if "max_tokens" not in kwargs:
            kwargs["max_tokens"] = 1024

        # Make API request
        response = self._make_request("messages", method="POST", data=kwargs)

        return response
