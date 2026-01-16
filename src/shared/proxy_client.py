"""
Oxylabs Proxy Integration Layer

Provides seamless switching between direct scraping and Oxylabs-proxied requests.
Supports both Residential Proxies and Web Scraper API.

Usage:
    from src.shared.proxy_client import ProxyClient, ProxyConfig

    # Configure client
    config = ProxyConfig.from_env()  # or ProxyConfig(...)
    client = ProxyClient(config)

    # Make requests (automatically uses configured proxy method)
    response = client.get(url)
    html_content = response.text
"""

import json
import logging
import os
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
import requests


class ProxyMode(Enum):
    """Proxy operation modes"""
    DIRECT = "direct"                    # No proxy, direct requests
    RESIDENTIAL = "residential"          # Oxylabs Residential Proxies
    WEB_SCRAPER_API = "web_scraper_api"  # Oxylabs Web Scraper API


@dataclass
class ProxyConfig:
    """Configuration for proxy client"""

    # Mode selection
    mode: ProxyMode = ProxyMode.DIRECT

    # Oxylabs credentials
    username: str = ""
    password: str = ""

    # Residential proxy settings
    residential_endpoint: str = "pr.oxylabs.io:7777"
    country_code: str = "us"  # Target country
    city: str = ""            # Optional city targeting
    state: str = ""           # Optional state targeting
    session_type: str = "rotating"  # "rotating" or "sticky"
    session_id: str = ""      # For sticky sessions

    # Web Scraper API settings
    scraper_api_endpoint: str = "https://realtime.oxylabs.io/v1/queries"
    render_js: bool = False   # Enable JavaScript rendering
    parse: bool = False       # Return parsed JSON instead of HTML

    # Request settings
    timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 2.0

    # Rate limiting (only applies to direct mode)
    min_delay: float = 0.0
    max_delay: float = 0.0

    @classmethod
    def from_env(cls) -> "ProxyConfig":
        """Create config from environment variables"""
        mode_str = os.getenv("PROXY_MODE", "direct").lower()
        mode_map = {
            "direct": ProxyMode.DIRECT,
            "residential": ProxyMode.RESIDENTIAL,
            "web_scraper_api": ProxyMode.WEB_SCRAPER_API,
            "scraper_api": ProxyMode.WEB_SCRAPER_API,
        }
        mode = mode_map.get(mode_str, ProxyMode.DIRECT)

        return cls(
            mode=mode,
            username=os.getenv("OXYLABS_USERNAME", ""),
            password=os.getenv("OXYLABS_PASSWORD", ""),
            country_code=os.getenv("OXYLABS_COUNTRY", "us"),
            city=os.getenv("OXYLABS_CITY", ""),
            state=os.getenv("OXYLABS_STATE", ""),
            render_js=os.getenv("OXYLABS_RENDER_JS", "false").lower() == "true",
            timeout=int(os.getenv("OXYLABS_TIMEOUT", "60")),
            max_retries=int(os.getenv("OXYLABS_MAX_RETRIES", "3")),
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProxyConfig":
        """Create config from dictionary (e.g., from YAML)"""
        mode_str = data.get("mode", "direct").lower()
        mode_map = {
            "direct": ProxyMode.DIRECT,
            "residential": ProxyMode.RESIDENTIAL,
            "web_scraper_api": ProxyMode.WEB_SCRAPER_API,
            "scraper_api": ProxyMode.WEB_SCRAPER_API,
        }
        mode = mode_map.get(mode_str, ProxyMode.DIRECT)

        return cls(
            mode=mode,
            username=data.get("username", os.getenv("OXYLABS_USERNAME", "")),
            password=data.get("password", os.getenv("OXYLABS_PASSWORD", "")),
            country_code=data.get("country_code", "us"),
            city=data.get("city", ""),
            state=data.get("state", ""),
            session_type=data.get("session_type", "rotating"),
            render_js=data.get("render_js", False),
            parse=data.get("parse", False),
            timeout=data.get("timeout", 60),
            max_retries=data.get("max_retries", 3),
            retry_delay=data.get("retry_delay", 2.0),
            min_delay=data.get("min_delay", 0.0),
            max_delay=data.get("max_delay", 0.0),
        )

    def is_enabled(self) -> bool:
        """Check if proxy is enabled (not direct mode)"""
        return self.mode != ProxyMode.DIRECT

    def validate(self) -> bool:
        """Validate configuration"""
        if self.mode == ProxyMode.DIRECT:
            return True

        if not self.username or not self.password:
            logging.error("Oxylabs credentials required for proxy mode")
            return False

        return True


@dataclass
class ProxyResponse:
    """Unified response object for all proxy modes"""

    status_code: int
    text: str
    content: bytes
    headers: Dict[str, str]
    url: str
    elapsed_seconds: float
    proxy_mode: ProxyMode

    # Additional metadata from Web Scraper API
    job_id: Optional[str] = None
    credits_used: Optional[float] = None

    @property
    def ok(self) -> bool:
        """Check if request was successful"""
        return 200 <= self.status_code < 300

    def json(self) -> Any:
        """Parse response as JSON"""
        return json.loads(self.text)

    def raise_for_status(self) -> None:
        """Raise exception for error status codes"""
        if not self.ok:
            raise requests.HTTPError(
                f"HTTP {self.status_code} for {self.url}",
                response=self
            )


class ProxyClient:
    """
    Unified proxy client supporting multiple Oxylabs products.

    Provides a consistent interface regardless of proxy mode:
    - Direct: Standard requests without proxy
    - Residential: Oxylabs Residential Proxy pool
    - Web Scraper API: Oxylabs managed scraping service
    """

    # User agents for rotation
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ]

    def __init__(self, config: Optional[ProxyConfig] = None):
        """
        Initialize proxy client.

        Args:
            config: Proxy configuration. If None, loads from environment.
        """
        self.config = config or ProxyConfig.from_env()
        self._session: Optional[requests.Session] = None
        self._request_count = 0

        if not self.config.validate():
            logging.warning("Invalid proxy config, falling back to direct mode")
            self.config.mode = ProxyMode.DIRECT

        logging.info(f"ProxyClient initialized in {self.config.mode.value} mode")

    @property
    def session(self) -> requests.Session:
        """Get or create requests session"""
        if self._session is None:
            self._session = requests.Session()
            self._configure_session()
        return self._session

    def _configure_session(self) -> None:
        """Configure session based on proxy mode"""
        if self.config.mode == ProxyMode.RESIDENTIAL:
            # Configure residential proxy
            proxy_url = self._build_residential_proxy_url()
            self._session.proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }
            logging.debug(f"Configured residential proxy: {self.config.residential_endpoint}")

    def _build_residential_proxy_url(self) -> str:
        """Build residential proxy URL with authentication and targeting"""
        # Build username with targeting options
        username_parts = [self.config.username]

        # Add country targeting
        if self.config.country_code:
            username_parts.append(f"country-{self.config.country_code}")

        # Add city targeting
        if self.config.city:
            username_parts.append(f"city-{self.config.city}")

        # Add state targeting
        if self.config.state:
            username_parts.append(f"state-{self.config.state}")

        # Add session type
        if self.config.session_type == "sticky" and self.config.session_id:
            username_parts.append(f"session-{self.config.session_id}")

        username = "-".join(username_parts)

        return f"http://{username}:{self.config.password}@{self.config.residential_endpoint}"

    def _get_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get request headers with random user agent"""
        headers = {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        if custom_headers:
            headers.update(custom_headers)

        return headers

    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        render_js: Optional[bool] = None,
        timeout: Optional[int] = None,
        **kwargs
    ) -> Optional[ProxyResponse]:
        """
        Make a GET request using configured proxy mode.

        Args:
            url: Target URL
            headers: Optional custom headers
            params: Optional query parameters
            render_js: Override JS rendering setting (Web Scraper API only)
            timeout: Request timeout in seconds
            **kwargs: Additional arguments passed to underlying request

        Returns:
            ProxyResponse object or None on failure
        """
        timeout = timeout or self.config.timeout
        render_js = render_js if render_js is not None else self.config.render_js

        for attempt in range(self.config.max_retries):
            try:
                if self.config.mode == ProxyMode.WEB_SCRAPER_API:
                    response = self._request_scraper_api(url, headers, params, render_js, timeout)
                else:
                    # Direct or Residential mode (both use requests session)
                    response = self._request_direct(url, headers, params, timeout, **kwargs)

                self._request_count += 1

                if response and response.ok:
                    # Apply delay for direct mode
                    if self.config.mode == ProxyMode.DIRECT and self.config.max_delay > 0:
                        delay = random.uniform(self.config.min_delay, self.config.max_delay)
                        time.sleep(delay)

                    return response

                # Handle rate limiting
                if response and response.status_code == 429:
                    wait_time = self.config.retry_delay * (2 ** attempt)
                    logging.warning(f"Rate limited, waiting {wait_time:.1f}s before retry")
                    time.sleep(wait_time)
                    continue

                # Handle server errors with retry
                if response and response.status_code >= 500:
                    logging.warning(f"Server error {response.status_code}, retrying...")
                    time.sleep(self.config.retry_delay)
                    continue

                # Client errors (4xx except 429) - don't retry
                if response and 400 <= response.status_code < 500:
                    logging.warning(f"Client error {response.status_code} for {url}")
                    return response

            except requests.exceptions.Timeout:
                logging.warning(f"Timeout on attempt {attempt + 1} for {url}")
                time.sleep(self.config.retry_delay)
            except requests.exceptions.RequestException as e:
                logging.warning(f"Request error on attempt {attempt + 1}: {e}")
                time.sleep(self.config.retry_delay)
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                time.sleep(self.config.retry_delay)

        logging.error(f"All {self.config.max_retries} attempts failed for {url}")
        return None

    def _request_direct(
        self,
        url: str,
        headers: Optional[Dict[str, str]],
        params: Optional[Dict[str, str]],
        timeout: int,
        **kwargs
    ) -> ProxyResponse:
        """Make request via direct connection or residential proxy"""
        start_time = time.time()

        response = self.session.get(
            url,
            headers=self._get_headers(headers),
            params=params,
            timeout=timeout,
            **kwargs
        )

        elapsed = time.time() - start_time

        return ProxyResponse(
            status_code=response.status_code,
            text=response.text,
            content=response.content,
            headers=dict(response.headers),
            url=str(response.url),
            elapsed_seconds=elapsed,
            proxy_mode=self.config.mode,
        )

    def _request_scraper_api(
        self,
        url: str,
        headers: Optional[Dict[str, str]],
        params: Optional[Dict[str, str]],
        render_js: bool,
        timeout: int,
    ) -> ProxyResponse:
        """Make request via Oxylabs Web Scraper API"""
        start_time = time.time()

        # Build full URL with params
        if params:
            from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
            parsed = urlparse(url)
            existing_params = parse_qs(parsed.query)
            existing_params.update(params)
            new_query = urlencode(existing_params, doseq=True)
            url = urlunparse(parsed._replace(query=new_query))

        # Build API payload
        payload = {
            "source": "universal",
            "url": url,
            "geo_location": self.config.country_code.upper() if self.config.country_code else None,
        }

        # Add JavaScript rendering if needed
        if render_js:
            payload["render"] = "html"

        # Add custom headers if provided
        if headers:
            payload["custom_headers"] = headers

        # Add parsing if configured
        if self.config.parse:
            payload["parse"] = True

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        # Make API request
        response = requests.post(
            self.config.scraper_api_endpoint,
            auth=(self.config.username, self.config.password),
            json=payload,
            timeout=timeout,
        )

        elapsed = time.time() - start_time

        # Parse API response
        if response.status_code == 200:
            api_response = response.json()
            results = api_response.get("results", [])

            if results:
                result = results[0]
                content = result.get("content", "")

                return ProxyResponse(
                    status_code=result.get("status_code", 200),
                    text=content,
                    content=content.encode("utf-8") if isinstance(content, str) else content,
                    headers={},
                    url=url,
                    elapsed_seconds=elapsed,
                    proxy_mode=ProxyMode.WEB_SCRAPER_API,
                    job_id=api_response.get("job_id"),
                    credits_used=api_response.get("credits_used"),
                )

        # Return error response
        return ProxyResponse(
            status_code=response.status_code,
            text=response.text,
            content=response.content,
            headers=dict(response.headers),
            url=url,
            elapsed_seconds=elapsed,
            proxy_mode=ProxyMode.WEB_SCRAPER_API,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            "mode": self.config.mode.value,
            "request_count": self._request_count,
            "country": self.config.country_code,
            "render_js": self.config.render_js,
        }

    def close(self) -> None:
        """Close the client session"""
        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self) -> "ProxyClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


# Convenience function for simple usage
def create_proxy_client(
    mode: str = "direct",
    username: str = "",
    password: str = "",
    **kwargs
) -> ProxyClient:
    """
    Create a proxy client with simple parameters.

    Args:
        mode: "direct", "residential", or "web_scraper_api"
        username: Oxylabs username
        password: Oxylabs password
        **kwargs: Additional ProxyConfig parameters

    Returns:
        Configured ProxyClient instance
    """
    mode_map = {
        "direct": ProxyMode.DIRECT,
        "residential": ProxyMode.RESIDENTIAL,
        "web_scraper_api": ProxyMode.WEB_SCRAPER_API,
        "scraper_api": ProxyMode.WEB_SCRAPER_API,
    }

    config = ProxyConfig(
        mode=mode_map.get(mode.lower(), ProxyMode.DIRECT),
        username=username or os.getenv("OXYLABS_USERNAME", ""),
        password=password or os.getenv("OXYLABS_PASSWORD", ""),
        **kwargs
    )

    return ProxyClient(config)
