"""Shared utility functions for all retailer scrapers"""

import json
import csv
import time
import random
import logging
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Union

import requests

# Import proxy client for Oxylabs integration
from src.shared.proxy_client import ProxyClient, ProxyConfig, ProxyMode, ProxyResponse


# Default configuration values (can be overridden per-retailer)
DEFAULT_MIN_DELAY = 2.0
DEFAULT_MAX_DELAY = 5.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
DEFAULT_RATE_LIMIT_BASE_WAIT = 30

# Default user agents for rotation
DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

# Global proxy client instance (lazy initialized)
_proxy_client: Optional[ProxyClient] = None


def setup_logging(log_file: str = "logs/scraper.log") -> None:
    """Setup logging configuration"""
    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )


def get_headers(user_agent: str = None, base_url: str = None) -> Dict[str, str]:
    """Get headers dict with optional user agent rotation"""
    if user_agent is None:
        user_agent = random.choice(DEFAULT_USER_AGENTS)

    return {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": base_url or "https://www.google.com",
    }


def random_delay(min_sec: float = None, max_sec: float = None) -> None:
    """Add randomized delay between requests"""
    min_sec = min_sec if min_sec is not None else DEFAULT_MIN_DELAY
    max_sec = max_sec if max_sec is not None else DEFAULT_MAX_DELAY
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)
    logging.debug(f"Delayed {delay:.2f} seconds")


def get_with_retry(
    session: requests.Session,
    url: str,
    max_retries: int = None,
    timeout: int = None,
    rate_limit_base_wait: int = None,
    min_delay: float = None,
    max_delay: float = None,
    headers_func = None,
) -> Optional[requests.Response]:
    """Fetch URL with exponential backoff retry and proper error handling

    Args:
        session: requests.Session to use
        url: URL to fetch
        max_retries: Maximum number of retry attempts
        timeout: Request timeout in seconds
        rate_limit_base_wait: Base wait time for 429 errors
        min_delay: Minimum delay between requests
        max_delay: Maximum delay between requests
        headers_func: Optional function to get headers (for config integration)
    """
    max_retries = max_retries if max_retries is not None else DEFAULT_MAX_RETRIES
    timeout = timeout if timeout is not None else DEFAULT_TIMEOUT
    rate_limit_base_wait = rate_limit_base_wait if rate_limit_base_wait is not None else DEFAULT_RATE_LIMIT_BASE_WAIT

    # Rotate user agent
    if headers_func:
        headers = headers_func()
    else:
        headers = get_headers()
    session.headers.update(headers)

    for attempt in range(max_retries):
        try:
            random_delay(min_delay, max_delay)
            response = session.get(url, timeout=timeout)

            if response.status_code == 200:
                logging.debug(f"Successfully fetched {url}")
                return response

            elif response.status_code == 429:  # Rate limited
                wait_time = (2 ** attempt) * rate_limit_base_wait
                logging.warning(f"Rate limited (429) for {url}. Waiting {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait_time)

            elif response.status_code == 403:  # Blocked
                logging.error(f"Blocked (403) for {url}. Waiting 5 minutes...")
                time.sleep(300)  # 5 minutes
                return None  # Don't retry 403, likely blocked

            elif response.status_code >= 500:  # Server error
                wait_time = 10
                logging.warning(f"Server error ({response.status_code}) for {url}. Waiting {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait_time)

            elif response.status_code == 408:  # Request timeout - might succeed on retry
                wait_time = 10
                logging.warning(f"Request timeout (408) for {url}. Waiting {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait_time)

            elif 400 <= response.status_code < 500:  # Client errors (4xx) - fail fast except 403/429/408
                # 404, 401, 410, etc. won't succeed on retry
                logging.error(f"Client error ({response.status_code}) for {url}. Failing immediately.")
                return None

            else:
                # 3xx redirects should be handled by requests library, but log unexpected codes
                logging.warning(f"Unexpected HTTP {response.status_code} for {url}")
                return None

        except requests.exceptions.RequestException as e:
            wait_time = 10
            logging.warning(f"Request error for {url}: {e}. Waiting {wait_time}s (attempt {attempt + 1}/{max_retries})...")
            time.sleep(wait_time)

    logging.error(f"Failed to fetch {url} after {max_retries} attempts")
    return None


def save_checkpoint(data: Any, filepath: str) -> None:
    """Save progress to allow resuming using atomic write (temp file + rename)"""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temporary file first, then rename atomically
    # This prevents corruption if interrupted during write
    try:
        # Create temp file in same directory to ensure atomic rename works
        temp_fd, temp_path = tempfile.mkstemp(
            suffix='.tmp',
            dir=path.parent,
            prefix=path.name + '.'
        )

        try:
            # Write JSON to temp file
            with open(temp_fd, 'w') as f:
                json.dump(data, f, indent=2)

            # Atomic rename: either succeeds completely or fails (no partial file)
            shutil.move(temp_path, path)
            logging.info(f"Checkpoint saved: {filepath}")

        except Exception as e:
            # Clean up temp file on error
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass
            raise e

    except (IOError, OSError) as e:
        logging.error(f"Failed to save checkpoint {filepath}: {e}")
        raise


def load_checkpoint(filepath: str) -> Optional[Any]:
    """Load previous progress"""
    path = Path(filepath)
    if not path.exists():
        return None

    try:
        with open(path, 'r') as f:
            data = json.load(f)
        logging.info(f"Checkpoint loaded: {filepath}")
        return data
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logging.warning(f"Failed to load checkpoint {filepath}: {e}")
        return None


def save_to_csv(stores: List[Dict[str, Any]], filepath: str, fieldnames: List[str] = None) -> None:
    """Save stores to CSV

    Args:
        stores: List of store dictionaries
        filepath: Path to save CSV file
        fieldnames: Optional list of field names (uses default if not provided)
    """
    if not stores:
        logging.warning("No stores to save")
        return

    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Default fieldnames for basic store data
    if fieldnames is None:
        fieldnames = ['name', 'street_address', 'city', 'state', 'zip',
                      'country', 'latitude', 'longitude', 'phone', 'url', 'scraped_at']

    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(stores)

    logging.info(f"Saved {len(stores)} stores to CSV: {filepath}")


def save_to_json(stores: List[Dict[str, Any]], filepath: str) -> None:
    """Save stores to JSON"""
    if not stores:
        logging.warning("No stores to save")
        return

    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(stores, f, indent=2, ensure_ascii=False)

    logging.info(f"Saved {len(stores)} stores to JSON: {filepath}")


# =============================================================================
# OXYLABS PROXY INTEGRATION
# =============================================================================

def get_proxy_client(config: Optional[Dict[str, Any]] = None) -> ProxyClient:
    """
    Get or create a proxy client instance.

    Args:
        config: Optional proxy configuration dictionary. If None, loads from
                environment variables.

    Returns:
        Configured ProxyClient instance
    """
    global _proxy_client

    if config is not None:
        # Create new client with provided config
        proxy_config = ProxyConfig.from_dict(config)
        return ProxyClient(proxy_config)

    if _proxy_client is None:
        # Create default client from environment
        _proxy_client = ProxyClient(ProxyConfig.from_env())

    return _proxy_client


def init_proxy_from_yaml(yaml_path: str = "config/retailers.yaml") -> ProxyClient:
    """
    Initialize proxy client from retailers.yaml configuration.

    Args:
        yaml_path: Path to retailers.yaml file

    Returns:
        Configured ProxyClient instance
    """
    global _proxy_client

    try:
        import yaml
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)

        proxy_config = config.get('proxy', {})
        mode = proxy_config.get('mode', 'direct')

        # Build config dict from YAML structure
        config_dict = {
            'mode': mode,
            'timeout': proxy_config.get('timeout', 60),
            'max_retries': proxy_config.get('max_retries', 3),
            'retry_delay': proxy_config.get('retry_delay', 2.0),
        }

        # Add mode-specific settings
        if mode == 'residential':
            res_config = proxy_config.get('residential', {})
            config_dict.update({
                'residential_endpoint': res_config.get('endpoint', 'pr.oxylabs.io:7777'),
                'country_code': res_config.get('country_code', 'us'),
                'session_type': res_config.get('session_type', 'rotating'),
            })
        elif mode == 'web_scraper_api':
            api_config = proxy_config.get('web_scraper_api', {})
            config_dict.update({
                'scraper_api_endpoint': api_config.get('endpoint', 'https://realtime.oxylabs.io/v1/queries'),
                'render_js': api_config.get('render_js', False),
                'parse': api_config.get('parse', False),
            })

        _proxy_client = get_proxy_client(config_dict)
        logging.info(f"Initialized proxy client from {yaml_path} in {mode} mode")
        return _proxy_client

    except FileNotFoundError:
        logging.warning(f"Config file {yaml_path} not found, using environment config")
        return get_proxy_client()
    except Exception as e:
        logging.warning(f"Error loading proxy config from {yaml_path}: {e}, using environment config")
        return get_proxy_client()


def get_with_proxy(
    url: str,
    proxy_config: Optional[Dict[str, Any]] = None,
    render_js: Optional[bool] = None,
    timeout: Optional[int] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Optional[Union[requests.Response, ProxyResponse]]:
    """
    Fetch URL using proxy client (Oxylabs integration).

    This is the recommended function for new code. It automatically handles:
    - Proxy rotation (residential mode)
    - JavaScript rendering (web_scraper_api mode)
    - Retries and rate limiting
    - CAPTCHA bypass (via Oxylabs)

    Args:
        url: URL to fetch
        proxy_config: Optional per-request proxy config override
        render_js: Override JS rendering (for web_scraper_api mode)
        timeout: Request timeout in seconds
        headers: Optional custom headers

    Returns:
        ProxyResponse object or None on failure
    """
    client = get_proxy_client(proxy_config)
    return client.get(url, headers=headers, render_js=render_js, timeout=timeout)


def create_proxied_session(
    retailer_config: Optional[Dict[str, Any]] = None
) -> Union[requests.Session, ProxyClient]:
    """
    Create a session-like object that can be used as a drop-in replacement
    for requests.Session in existing scrapers.

    For direct mode, returns a standard requests.Session.
    For proxy modes, returns a ProxyClient with compatible interface.

    Args:
        retailer_config: Optional retailer-specific config with proxy overrides

    Returns:
        Session-compatible object
    """
    # Check for retailer-specific proxy override
    proxy_config = None
    if retailer_config and 'proxy' in retailer_config:
        proxy_config = retailer_config['proxy']

    # Get global proxy config
    client = get_proxy_client(proxy_config)

    if client.config.mode == ProxyMode.DIRECT:
        # Return standard session for backward compatibility
        session = requests.Session()
        session.headers.update(get_headers())
        return session

    # Return proxy client (has compatible .get() method)
    return client


def close_proxy_client() -> None:
    """Close the global proxy client and release resources."""
    global _proxy_client
    if _proxy_client is not None:
        _proxy_client.close()
        _proxy_client = None
        logging.info("Proxy client closed")


class ProxiedSession:
    """
    A wrapper that provides requests.Session-like interface but uses
    ProxyClient under the hood. This allows existing scrapers to work
    with minimal changes.

    Usage:
        # Instead of: session = requests.Session()
        session = ProxiedSession(proxy_config)
        response = session.get(url)  # Uses proxy if configured
    """

    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None):
        """
        Initialize proxied session.

        Args:
            proxy_config: Optional proxy configuration dict
        """
        self._client = get_proxy_client(proxy_config)
        self._direct_session: Optional[requests.Session] = None
        self.headers: Dict[str, str] = get_headers()

    @property
    def _session(self) -> requests.Session:
        """Lazy-create direct session if needed"""
        if self._direct_session is None:
            self._direct_session = requests.Session()
            self._direct_session.headers.update(self.headers)
        return self._direct_session

    def get(
        self,
        url: str,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        **kwargs
    ) -> Optional[Union[requests.Response, ProxyResponse]]:
        """
        Make GET request using configured proxy mode.

        Args:
            url: URL to fetch
            params: Query parameters
            headers: Custom headers
            timeout: Request timeout
            **kwargs: Additional arguments (passed to underlying client)

        Returns:
            Response object or None on failure
        """
        merged_headers = {**self.headers, **(headers or {})}

        if self._client.config.mode == ProxyMode.DIRECT:
            # Use standard session for direct mode
            try:
                self._session.headers.update(merged_headers)
                response = self._session.get(url, params=params, timeout=timeout or 30, **kwargs)
                return response
            except requests.exceptions.RequestException as e:
                logging.warning(f"Request error: {e}")
                return None
        else:
            # Use proxy client
            return self._client.get(url, params=params, headers=merged_headers, timeout=timeout)

    def close(self) -> None:
        """Close the session"""
        if self._direct_session:
            self._direct_session.close()
            self._direct_session = None

    def __enter__(self) -> "ProxiedSession":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
