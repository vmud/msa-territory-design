"""Shared utilities for all scrapers"""

from .utils import (
    setup_logging,
    random_delay,
    get_with_retry,
    get_headers,
    save_checkpoint,
    load_checkpoint,
    save_to_csv,
    save_to_json,
    DEFAULT_MIN_DELAY,
    DEFAULT_MAX_DELAY,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    DEFAULT_RATE_LIMIT_BASE_WAIT,
    DEFAULT_USER_AGENTS,
    # Oxylabs proxy integration
    get_proxy_client,
    get_with_proxy,
    init_proxy_from_yaml,
    create_proxied_session,
    close_proxy_client,
    ProxiedSession,
)

from .proxy_client import (
    ProxyClient,
    ProxyConfig,
    ProxyMode,
    ProxyResponse,
    create_proxy_client,
)

__all__ = [
    # Core utilities
    'setup_logging',
    'random_delay',
    'get_with_retry',
    'get_headers',
    'save_checkpoint',
    'load_checkpoint',
    'save_to_csv',
    'save_to_json',
    'DEFAULT_MIN_DELAY',
    'DEFAULT_MAX_DELAY',
    'DEFAULT_MAX_RETRIES',
    'DEFAULT_TIMEOUT',
    'DEFAULT_RATE_LIMIT_BASE_WAIT',
    'DEFAULT_USER_AGENTS',
    # Oxylabs proxy integration
    'ProxyClient',
    'ProxyConfig',
    'ProxyMode',
    'ProxyResponse',
    'create_proxy_client',
    'get_proxy_client',
    'get_with_proxy',
    'init_proxy_from_yaml',
    'create_proxied_session',
    'close_proxy_client',
    'ProxiedSession',
]
