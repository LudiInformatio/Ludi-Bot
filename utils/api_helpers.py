"""
LUDI INFORMATIO | API HELPER UTILITIES
=======================================
Retry logic, error handling, and request wrappers for robust API interactions.

Features:
- Retry decorator with exponential backoff
- Specific handling for rate limits (429), server errors (5xx), auth errors (401/403)
- Circuit breaker pattern to prevent cascading failures
- Integration with API monitoring for logging

Usage:
    from utils.api_helpers import retry_with_backoff

    @retry_with_backoff(max_attempts=3, backoff=2.0)
    def fetch_data(url):
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
"""

import time
import requests
from functools import wraps
from typing import Callable, Optional
from datetime import datetime, timedelta


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent repeated calls to failing endpoints.

    States:
    - CLOSED: Normal operation
    - OPEN: Too many failures, reject calls immediately
    - HALF_OPEN: Testing if endpoint has recovered
    """

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before trying again (HALF_OPEN state)
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN

    def call(self, func: Callable, *args, **kwargs):
        """Execute function through circuit breaker."""
        if self.state == 'OPEN':
            # Check if timeout has elapsed
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = 'HALF_OPEN'
                print(f"      🔄 Circuit breaker HALF_OPEN: Testing endpoint...")
            else:
                raise Exception(f"Circuit breaker OPEN: Endpoint failing, try again in {self.timeout}s")

        try:
            result = func(*args, **kwargs)
            # Success - reset circuit
            if self.state == 'HALF_OPEN':
                print(f"      ✅ Circuit breaker CLOSED: Endpoint recovered")
            self.failure_count = 0
            self.state = 'CLOSED'
            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                print(f"      ⚠️ Circuit breaker OPEN: Too many failures ({self.failure_count})")

            raise e


# Global circuit breakers for different APIs
_circuit_breakers = {}

def get_circuit_breaker(api_name: str) -> CircuitBreaker:
    """Get or create circuit breaker for an API."""
    if api_name not in _circuit_breakers:
        _circuit_breakers[api_name] = CircuitBreaker()
    return _circuit_breakers[api_name]


def retry_with_backoff(max_attempts: int = 3, backoff: float = 2.0,
                       exceptions: tuple = (requests.RequestException,)):
    """
    Decorator to retry function with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default 3)
        backoff: Base backoff multiplier in seconds (default 2.0)
        exceptions: Tuple of exceptions to catch and retry

    Example:
        @retry_with_backoff(max_attempts=3, backoff=2.0)
        def fetch_data(url):
            return requests.get(url).json()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1

            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)

                except requests.exceptions.HTTPError as e:
                    status_code = e.response.status_code if e.response else None

                    # Handle specific HTTP errors
                    if status_code == 401 or status_code == 403:
                        # Authentication error - don't retry
                        print(f"      ❌ AUTH ERROR ({status_code}): Check API key")
                        raise Exception(f"Authentication failed (HTTP {status_code}). Verify API key in .env file.")

                    elif status_code == 429:
                        # Rate limit - wait longer
                        wait_time = backoff * (2 ** (attempt - 1)) * 2  # Double wait time for rate limits
                        print(f"      ⏳ RATE LIMIT (429): Waiting {wait_time:.1f}s before retry {attempt}/{max_attempts}")

                        if attempt < max_attempts:
                            time.sleep(wait_time)
                            attempt += 1
                            continue
                        else:
                            raise Exception(f"Rate limit exceeded after {max_attempts} attempts. Try again later.")

                    elif status_code and status_code >= 500:
                        # Server error - retry with backoff
                        wait_time = backoff * (2 ** (attempt - 1))
                        print(f"      ⚠️ SERVER ERROR ({status_code}): Retrying in {wait_time:.1f}s ({attempt}/{max_attempts})")

                        if attempt < max_attempts:
                            time.sleep(wait_time)
                            attempt += 1
                            continue
                        else:
                            raise Exception(f"Server error ({status_code}) persisted after {max_attempts} attempts.")

                    else:
                        # Other HTTP errors - raise immediately
                        raise

                except requests.exceptions.ConnectionError as e:
                    # Network error - retry with backoff
                    wait_time = backoff * (2 ** (attempt - 1))
                    print(f"      🌐 NETWORK ERROR: Retrying in {wait_time:.1f}s ({attempt}/{max_attempts})")

                    if attempt < max_attempts:
                        time.sleep(wait_time)
                        attempt += 1
                        continue
                    else:
                        raise Exception(f"Network connection failed after {max_attempts} attempts. Check internet connection.")

                except requests.exceptions.Timeout as e:
                    # Timeout - retry with backoff
                    wait_time = backoff * (2 ** (attempt - 1))
                    print(f"      ⏱️ TIMEOUT: Retrying in {wait_time:.1f}s ({attempt}/{max_attempts})")

                    if attempt < max_attempts:
                        time.sleep(wait_time)
                        attempt += 1
                        continue
                    else:
                        raise Exception(f"Request timed out after {max_attempts} attempts.")

                except exceptions as e:
                    # Other specified exceptions - retry
                    wait_time = backoff * (2 ** (attempt - 1))
                    print(f"      ⚠️ ERROR: {type(e).__name__}: {str(e)[:100]}")
                    print(f"      Retrying in {wait_time:.1f}s ({attempt}/{max_attempts})")

                    if attempt < max_attempts:
                        time.sleep(wait_time)
                        attempt += 1
                        continue
                    else:
                        raise

        return wrapper
    return decorator


def check_response_status(response: requests.Response, api_name: str = 'API') -> requests.Response:
    """
    Check response status and log useful information.

    Args:
        response: requests.Response object
        api_name: Name of API for logging

    Returns:
        response object if successful

    Raises:
        HTTPError if status code indicates error
    """
    if response.status_code == 200:
        return response
    elif response.status_code == 401:
        raise requests.exceptions.HTTPError(
            f"{api_name} authentication failed (401). Check API key.",
            response=response
        )
    elif response.status_code == 403:
        raise requests.exceptions.HTTPError(
            f"{api_name} access forbidden (403). Check API permissions or tier.",
            response=response
        )
    elif response.status_code == 429:
        raise requests.exceptions.HTTPError(
            f"{api_name} rate limit exceeded (429). Slow down requests.",
            response=response
        )
    elif response.status_code >= 500:
        raise requests.exceptions.HTTPError(
            f"{api_name} server error ({response.status_code}). Try again later.",
            response=response
        )
    else:
        response.raise_for_status()

    return response


def safe_api_call(api_name: str, func: Callable, *args, use_circuit_breaker: bool = True, **kwargs):
    """
    Wrapper for API calls with circuit breaker pattern.

    Args:
        api_name: Name of API (for circuit breaker tracking)
        func: Function to call
        use_circuit_breaker: Whether to use circuit breaker (default True)
        *args, **kwargs: Arguments to pass to func

    Returns:
        Result of func call

    Example:
        result = safe_api_call('odds_api', requests.get, url, params=params)
    """
    if use_circuit_breaker:
        breaker = get_circuit_breaker(api_name)
        return breaker.call(func, *args, **kwargs)
    else:
        return func(*args, **kwargs)


def parse_rate_limit_headers(headers: dict, api_type: str = 'odds_api') -> dict:
    """
    Parse rate limit information from response headers.

    Args:
        headers: Response headers dict
        api_type: 'odds_api' or 'tank01'

    Returns:
        Dictionary with rate limit info
    """
    if api_type == 'odds_api':
        return {
            'remaining': headers.get('x-requests-remaining', 'Unknown'),
            'used': headers.get('x-requests-used', 'Unknown'),
            'last_cost': headers.get('x-requests-last', 'Unknown')
        }
    elif api_type == 'tank01':
        return {
            'remaining': headers.get('x-ratelimit-requests-remaining',
                                    headers.get('x-ratelimit-remaining', 'Unknown')),
            'limit': headers.get('x-ratelimit-requests-limit',
                                headers.get('x-ratelimit-limit', 'Unknown'))
        }
    else:
        return {'error': 'Unknown API type'}


# Example usage demonstration
if __name__ == "__main__":
    print("API Helpers Utility - Example Usage\n")

    # Example 1: Simple retry
    @retry_with_backoff(max_attempts=3)
    def test_api_call():
        print("Making API call...")
        # Simulating an API call
        return {"status": "success"}

    try:
        result = test_api_call()
        print(f"✅ Result: {result}")
    except Exception as e:
        print(f"❌ Failed: {e}")

    # Example 2: Circuit breaker
    print("\n--- Circuit Breaker Example ---")
    breaker = get_circuit_breaker('test_api')
    print(f"Initial state: {breaker.state}")
    print(f"Failure count: {breaker.failure_count}")
