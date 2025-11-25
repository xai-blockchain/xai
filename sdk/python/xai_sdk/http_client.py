"""
HTTP Client for XAI SDK

Handles all HTTP communication with retry logic, connection pooling,
and error handling.
"""

import requests
import time
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from .exceptions import (
    XAIError,
    AuthenticationError,
    RateLimitError,
    NetworkError,
    TimeoutError,
    NotFoundError,
    ValidationError,
    InternalServerError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)


class HTTPClient:
    """
    HTTP client for making API requests with retry logic and connection pooling.

    Features:
    - Automatic retry with exponential backoff
    - Connection pooling
    - Rate limit handling
    - Comprehensive error handling
    - Request logging
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        pool_connections: int = 10,
        pool_maxsize: int = 10,
    ) -> None:
        """
        Initialize HTTP client.

        Args:
            base_url: Base URL for API
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            backoff_factor: Backoff factor for exponential backoff
            pool_connections: Number of connection pools
            pool_maxsize: Maximum size of connection pool
        """
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        # Configure session with connection pooling
        self.session = requests.Session()
        self._setup_connection_pooling(pool_connections, pool_maxsize)
        self._setup_retry_strategy()

    def _setup_connection_pooling(
        self, pool_connections: int, pool_maxsize: int
    ) -> None:
        """Setup HTTP connection pooling."""
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=Retry(
                total=self.max_retries,
                backoff_factor=self.backoff_factor,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET", "POST", "PUT", "DELETE"],
            ),
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _setup_retry_strategy(self) -> None:
        """Setup retry strategy."""
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _get_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get request headers with authentication.

        Args:
            custom_headers: Custom headers to include

        Returns:
            Headers dictionary
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "XAI-SDK/1.0",
        }

        if self.api_key:
            headers["X-API-Key"] = self.api_key

        if custom_headers:
            headers.update(custom_headers)

        return headers

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle API response and raise appropriate exceptions.

        Args:
            response: Response object

        Returns:
            Response data

        Raises:
            Various XAI exceptions based on status code
        """
        try:
            data = response.json()
        except ValueError:
            data = {"message": response.text}

        if 200 <= response.status_code < 300:
            return data

        # Handle error responses
        error_message = data.get("message", data.get("error", "Unknown error"))
        error_code = data.get("code", response.status_code)

        if response.status_code == 400:
            raise ValidationError(error_message, code=error_code)
        elif response.status_code == 401:
            raise AuthenticationError(error_message, code=error_code)
        elif response.status_code == 404:
            raise NotFoundError(error_message, code=error_code)
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                error_message,
                retry_after=int(retry_after) if retry_after else None,
                code=error_code,
            )
        elif response.status_code == 500:
            raise InternalServerError(error_message, code=error_code)
        elif response.status_code == 503:
            raise ServiceUnavailableError(error_message, code=error_code)
        else:
            raise XAIError(error_message, code=error_code)

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a GET request.

        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Custom headers

        Returns:
            Response data
        """
        url = urljoin(self.base_url, endpoint)
        headers = self._get_headers(headers)

        try:
            response = self.session.get(
                url, params=params, headers=headers, timeout=self.timeout
            )
            logger.debug(f"GET {url} - Status: {response.status_code}")
            return self._handle_response(response)
        except requests.Timeout as e:
            logger.error(f"Request timeout: {e}")
            raise TimeoutError(f"Request timeout after {self.timeout}s")
        except requests.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise NetworkError(f"Connection error: {str(e)}")
        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            raise NetworkError(f"Request error: {str(e)}")

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a POST request.

        Args:
            endpoint: API endpoint
            data: Request body data
            headers: Custom headers

        Returns:
            Response data
        """
        url = urljoin(self.base_url, endpoint)
        headers = self._get_headers(headers)

        try:
            response = self.session.post(
                url, json=data, headers=headers, timeout=self.timeout
            )
            logger.debug(f"POST {url} - Status: {response.status_code}")
            return self._handle_response(response)
        except requests.Timeout as e:
            logger.error(f"Request timeout: {e}")
            raise TimeoutError(f"Request timeout after {self.timeout}s")
        except requests.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise NetworkError(f"Connection error: {str(e)}")
        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            raise NetworkError(f"Request error: {str(e)}")

    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a PUT request.

        Args:
            endpoint: API endpoint
            data: Request body data
            headers: Custom headers

        Returns:
            Response data
        """
        url = urljoin(self.base_url, endpoint)
        headers = self._get_headers(headers)

        try:
            response = self.session.put(
                url, json=data, headers=headers, timeout=self.timeout
            )
            logger.debug(f"PUT {url} - Status: {response.status_code}")
            return self._handle_response(response)
        except requests.Timeout as e:
            logger.error(f"Request timeout: {e}")
            raise TimeoutError(f"Request timeout after {self.timeout}s")
        except requests.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise NetworkError(f"Connection error: {str(e)}")
        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            raise NetworkError(f"Request error: {str(e)}")

    def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a DELETE request.

        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Custom headers

        Returns:
            Response data
        """
        url = urljoin(self.base_url, endpoint)
        headers = self._get_headers(headers)

        try:
            response = self.session.delete(
                url, params=params, headers=headers, timeout=self.timeout
            )
            logger.debug(f"DELETE {url} - Status: {response.status_code}")
            return self._handle_response(response)
        except requests.Timeout as e:
            logger.error(f"Request timeout: {e}")
            raise TimeoutError(f"Request timeout after {self.timeout}s")
        except requests.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise NetworkError(f"Connection error: {str(e)}")
        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            raise NetworkError(f"Request error: {str(e)}")

    def close(self) -> None:
        """Close the session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
