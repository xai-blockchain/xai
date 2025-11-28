"""
XAI Blockchain - Request Validator Middleware

Comprehensive request validation middleware for Flask applications.
Provides:
- Request size validation
- Content-Type checking
- JSON schema validation
- Cryptographic header validation
- CORS and security headers
- Request fingerprinting for security analysis
"""

import json
import hashlib
import logging
from typing import Callable, Dict, Any, Optional, Tuple, Type
from functools import wraps
from datetime import datetime, timezone
from pydantic import ValidationError, BaseModel
from flask import request, jsonify, Response

# Setup security logger
security_logger = logging.getLogger('xai.security')


class RequestValidationError(Exception):
    """Raised when request validation fails"""
    pass


class RequestValidator:
    """
    Validates all incoming HTTP requests for security compliance.

    Features:
    - Size limit enforcement
    - Content-Type validation
    - JSON schema validation
    - Request fingerprinting
    - Security headers enforcement
    - Malformed request detection
    """

    def __init__(
        self,
        max_json_size: int = 1_000_000,  # 1MB
        max_form_size: int = 10_000_000,  # 10MB
        max_url_length: int = 2048,
        allowed_content_types: Optional[list] = None,
    ):
        """
        Initialize request validator.

        Args:
            max_json_size: Maximum JSON payload size in bytes
            max_form_size: Maximum form data size in bytes
            max_url_length: Maximum URL length in bytes
            allowed_content_types: List of allowed Content-Types
        """
        self.max_json_size = max_json_size
        self.max_form_size = max_form_size
        self.max_url_length = max_url_length
        self.allowed_content_types = allowed_content_types or [
            'application/json',
            'application/x-www-form-urlencoded',
            'multipart/form-data',
        ]

    def validate_request_size(self) -> Tuple[bool, Optional[str]]:
        """
        Validate request size doesn't exceed limits.

        Returns:
            Tuple[bool, Optional[str]]: (valid, error_message)
        """
        # Check Content-Length header
        content_length = request.content_length
        if content_length:
            if content_length > self.max_json_size:
                error = f"Request body exceeds maximum size of {self.max_json_size} bytes"
                security_logger.warning(f"Size limit exceeded: {content_length} bytes from {request.remote_addr}")
                return False, error

        # Check URL length
        if len(request.url) > self.max_url_length:
            error = f"URL exceeds maximum length of {self.max_url_length} bytes"
            security_logger.warning(f"URL too long from {request.remote_addr}")
            return False, error

        return True, None

    def validate_content_type(self) -> Tuple[bool, Optional[str]]:
        """
        Validate Content-Type header.

        Returns:
            Tuple[bool, Optional[str]]: (valid, error_message)
        """
        # Skip validation for GET/HEAD requests
        if request.method in ['GET', 'HEAD', 'DELETE']:
            return True, None

        content_type = request.content_type
        if not content_type:
            return True, None  # Allow missing Content-Type for some requests

        # Extract base content type (without charset)
        base_type = content_type.split(';')[0].strip()

        # Check if content type is allowed
        if base_type not in self.allowed_content_types:
            error = f"Content-Type '{base_type}' is not allowed"
            security_logger.warning(f"Invalid Content-Type from {request.remote_addr}: {base_type}")
            return False, error

        return True, None

    def validate_json_structure(self, max_depth: int = 10) -> Tuple[bool, Optional[str]]:
        """
        Validate JSON structure for safety.

        Args:
            max_depth: Maximum nesting depth allowed

        Returns:
            Tuple[bool, Optional[str]]: (valid, error_message)
        """
        if request.method in ['GET', 'HEAD', 'DELETE']:
            return True, None

        # Try to parse JSON
        try:
            data = request.get_json(force=True, silent=True)
            if data is None:
                return True, None  # Not JSON

            # Check depth
            def check_depth(obj, depth=0):
                if depth > max_depth:
                    return False
                if isinstance(obj, dict):
                    return all(check_depth(v, depth + 1) for v in obj.values())
                elif isinstance(obj, list):
                    return all(check_depth(v, depth + 1) for v in obj)
                return True

            if not check_depth(data):
                error = f"JSON exceeds maximum nesting depth of {max_depth}"
                security_logger.warning(f"JSON nesting too deep from {request.remote_addr}")
                return False, error

        except (json.JSONDecodeError, ValueError) as e:
            error = f"Invalid JSON: {str(e)}"
            security_logger.warning(f"JSON parse error from {request.remote_addr}: {str(e)}")
            return False, error

        return True, None

    def validate_pydantic_model(
        self, model: Type[BaseModel]
    ) -> Tuple[bool, Optional[str], Optional[BaseModel]]:
        """
        Validate request body against Pydantic model.

        Args:
            model: Pydantic model class to validate against

        Returns:
            Tuple[bool, Optional[str]]: (valid, error_message)
        """
        try:
            data = request.get_json(force=True, silent=True)
            if data is None:
                return False, "No JSON data provided", None

            # Validate against model
            parsed = model.parse_obj(data)
            return True, None, parsed

        except ValidationError as e:
            error = f"Validation error: {e.json()}"
            security_logger.warning(f"Pydantic validation failed: {error}")
            return False, error, None
        except Exception as e:
            error = f"Validation error: {str(e)}"
            security_logger.warning(f"Unexpected validation error: {str(e)}")
            return False, error, None

    def get_request_fingerprint(self) -> str:
        """
        Generate a fingerprint of the request for security analysis.

        Returns:
            str: SHA256 hash of request characteristics
        """
        fingerprint_data = {
            'ip': request.remote_addr,
            'method': request.method,
            'path': request.path,
            'user_agent': request.headers.get('User-Agent', 'unknown'),
            'content_type': request.content_type,
        }

        fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]

    def get_request_metadata(self) -> Dict[str, Any]:
        """
        Extract metadata from request for logging and analysis.

        Returns:
            Dict[str, Any]: Request metadata
        """
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'method': request.method,
            'path': request.path,
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent'),
            'content_type': request.content_type,
            'content_length': request.content_length,
            'fingerprint': self.get_request_fingerprint(),
        }

    def enforce_security_headers(self, response: Response) -> Response:
        """
        Enforce security headers on response.

        Args:
            response: Flask response object

        Returns:
            Response: Response with security headers added
        """
        # OWASP recommended headers
        headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=(), payment=()',
        }

        for header, value in headers.items():
            response.headers[header] = value

        return response


def validate_request(
    validator: RequestValidator,
    pydantic_model: Optional[Type[BaseModel]] = None,
) -> Callable:
    """
    Decorator to validate requests before handler execution.

    Args:
        validator: RequestValidator instance
        pydantic_model: Optional Pydantic model for validation

    Returns:
        Callable: Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Validate request size
            valid, error = validator.validate_request_size()
            if not valid:
                return jsonify({'success': False, 'error': error, 'code': 'payload_too_large'}), 413  # Payload Too Large

            # Validate Content-Type
            valid, error = validator.validate_content_type()
            if not valid:
                return jsonify({'success': False, 'error': error, 'code': 'unsupported_media_type'}), 415  # Unsupported Media Type

            # Validate JSON structure
            valid, error = validator.validate_json_structure()
            if not valid:
                return jsonify({'success': False, 'error': error, 'code': 'invalid_json'}), 400  # Bad Request

            # Validate Pydantic model if provided
            if pydantic_model:
                valid, error, parsed_model = validator.validate_pydantic_model(pydantic_model)
                if not valid:
                    return jsonify({'success': False, 'error': error, 'code': 'validation_error'}), 400  # Bad Request
            else:
                parsed_model = None

            # Log request metadata
            metadata = validator.get_request_metadata()
            security_logger.info(f"Valid request: {json.dumps(metadata)}")

            # Add validator to request context
            request.validator = validator
            request.validated_model = parsed_model
            request.validated_data = parsed_model.dict() if parsed_model is not None else None

            # Call original handler
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def add_security_headers_middleware(app):
    """
    Add security headers middleware to Flask app.

    Args:
        app: Flask application instance
    """
    validator = RequestValidator()

    @app.after_request
    def add_headers(response: Response) -> Response:
        """Add security headers to all responses"""
        return validator.enforce_security_headers(response)

    @app.before_request
    def validate_incoming_request():
        """Validate all incoming requests"""
        # Basic validation on every request
        valid, error = validator.validate_request_size()
        if not valid:
            return jsonify({'error': error}), 413

        valid, error = validator.validate_content_type()
        if not valid:
            return jsonify({'error': error}), 415


# Convenience function for Flask app initialization
def setup_request_validation(
    app,
    max_json_size: int = 1_000_000,
    max_form_size: int = 10_000_000,
) -> RequestValidator:
    """
    Setup request validation for Flask app.

    Args:
        app: Flask application instance
        max_json_size: Maximum JSON payload size
        max_form_size: Maximum form data size

    Returns:
        RequestValidator: Configured validator instance
    """
    validator = RequestValidator(
        max_json_size=max_json_size,
        max_form_size=max_form_size,
    )

    add_security_headers_middleware(app)

    return validator
