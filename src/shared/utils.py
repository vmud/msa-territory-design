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
from typing import Optional, Dict, Any, List

import requests


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
