# Technical Specification: Per-Retailer Proxy Configuration

## Task Difficulty: Medium

This task involves moderate complexity with several interconnected components, multiple configuration layers, and requires careful handling of proxy switching during runtime.

## Overview

Currently, the scraper supports three proxy modes (direct, residential, web_scraper_api) configured globally via environment variables or CLI flags. This specification describes how to enable per-retailer proxy configuration, allowing each retailer to use its optimal proxy method and enabling automatic switching when running multiple retailers concurrently.

## Technical Context

- **Language**: Python 3.11+
- **Key Dependencies**: 
  - requests (HTTP client)
  - PyYAML (configuration parsing)
  - BeautifulSoup4 (HTML parsing)
- **Current Architecture**:
  - Global `ProxyClient` instance managed in `src/shared/utils.py`
  - Proxy configuration via environment variables or `retailers.yaml`
  - Scrapers use `utils.get_with_retry()` which uses the global proxy client
  - `run.py` CLI initializes proxy once at startup

## Current Limitations

1. **Single Global Proxy Mode**: The `PROXY_MODE` environment variable and `--proxy` CLI flag set one mode for all retailers
2. **No Per-Retailer Override**: While `retailers.yaml` has commented proxy override sections per retailer, they are not implemented
3. **Static Configuration**: Proxy mode cannot change during a multi-retailer run
4. **Inefficient Resource Usage**: All retailers must use the same proxy method even if some don't need it

## Requirements

1. Each retailer should have a configurable proxy mode in `retailers.yaml`
2. When running multiple retailers, the system should switch proxy modes automatically
3. CLI `--proxy` flag should override per-retailer settings (global override)
4. Default to `direct` mode if no retailer-specific or global configuration exists
5. Maintain backward compatibility with existing environment variable configuration
6. Support all three modes: `direct`, `residential`, `web_scraper_api`

## Implementation Approach

### 1. Configuration Layer (`config/retailers.yaml`)

Enable per-retailer proxy configuration by activating the existing commented-out proxy sections:

```yaml
retailers:
  verizon:
    proxy:
      mode: "residential"  # or "direct" or "web_scraper_api"
      render_js: false
      
  walmart:
    proxy:
      mode: "web_scraper_api"
      render_js: true
      
  att:
    proxy:
      mode: "direct"  # No proxy
```

**Configuration Resolution Priority**:
1. CLI flag (`--proxy`) - overrides everything
2. Retailer-specific config in `retailers.yaml`
3. Global proxy section in `retailers.yaml`
4. Environment variable (`PROXY_MODE`)
5. Default: `direct`

### 2. Proxy Client Management (`src/shared/utils.py`)

**Current**: Single global `_proxy_client` instance

**New**: Retailer-specific proxy client management

- Modify `get_proxy_client()` to accept `retailer` parameter
- Maintain a dictionary of proxy clients per retailer
- Create clients lazily on first request
- Properly clean up all clients on shutdown

```python
# Conceptual signature changes
_proxy_clients: Dict[str, ProxyClient] = {}

def get_proxy_client(
    config: Optional[Dict[str, Any]] = None,
    retailer: Optional[str] = None
) -> ProxyClient:
    """Get proxy client for specific retailer or global default"""
    ...

def close_all_proxy_clients() -> None:
    """Close all proxy client sessions"""
    ...
```

### 3. Configuration Loading (`src/shared/utils.py`)

Add function to load retailer-specific proxy configuration:

```python
def get_retailer_proxy_config(
    retailer: str,
    yaml_path: str = "config/retailers.yaml",
    cli_override: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get proxy configuration for specific retailer.
    
    Applies configuration priority rules.
    Returns dict compatible with ProxyConfig.from_dict()
    """
    ...
```

### 4. Request Utilities (`src/shared/utils.py`)

Update request functions to support per-retailer proxy:

- `get_with_retry()`: Add `retailer` parameter
- `get_with_proxy()`: Add `retailer` parameter
- `create_proxied_session()`: Add `retailer` parameter

### 5. Scraper Integration (`src/scrapers/*.py`)

Each scraper module needs minimal changes:

- Pass `retailer` identifier to `get_with_retry()` calls
- No changes to scraper logic, only parameter addition

Example:
```python
# Before
response = utils.get_with_retry(session, url)

# After
response = utils.get_with_retry(session, url, retailer='verizon')
```

### 6. CLI Integration (`run.py`)

- Keep `--proxy` flag for global override
- Pass CLI override value to configuration loading
- Pass retailer name when initializing scrapers
- Handle cleanup of multiple proxy clients on shutdown

## Source Code Structure Changes

### Files to Modify

1. **`config/retailers.yaml`** (60 lines affected)
   - Uncomment and configure `proxy:` sections for each retailer
   - Set appropriate modes based on retailer requirements

2. **`src/shared/utils.py`** (~150 lines affected)
   - Add `get_retailer_proxy_config()` function
   - Modify `get_proxy_client()` to support retailer parameter
   - Update `get_with_retry()`, `get_with_proxy()` signatures
   - Add `close_all_proxy_clients()` cleanup function
   - Change global `_proxy_client` to `_proxy_clients` dict

3. **`src/shared/__init__.py`** (5 lines)
   - Export new functions

4. **`run.py`** (~30 lines affected)
   - Pass CLI proxy override to configuration system
   - Pass retailer name to scraper execution functions
   - Add cleanup call for all proxy clients

5. **`src/scrapers/verizon.py`** (~10 locations)
   - Add `retailer='verizon'` parameter to `get_with_retry()` calls

6. **`src/scrapers/att.py`** (~10 locations)
   - Add `retailer='att'` parameter to `get_with_retry()` calls

7. **`src/scrapers/target.py`** (~10 locations)
   - Add `retailer='target'` parameter to `get_with_retry()` calls

8. **`src/scrapers/tmobile.py`** (~10 locations)
   - Add `retailer='tmobile'` parameter to `get_with_retry()` calls

9. **`src/scrapers/walmart.py`** (~10 locations)
   - Add `retailer='walmart'` parameter to `get_with_retry()` calls

10. **`src/scrapers/bestbuy.py`** (~10 locations)
    - Add `retailer='bestbuy'` parameter to `get_with_retry()` calls

### Files to Create

None. All changes are modifications to existing files.

## Data Model / API / Interface Changes

### ProxyConfig

No changes to the `ProxyConfig` class itself. Configuration resolution happens before instantiation.

### get_proxy_client()

```python
# Old signature
def get_proxy_client(config: Optional[Dict[str, Any]] = None) -> ProxyClient

# New signature (backward compatible)
def get_proxy_client(
    config: Optional[Dict[str, Any]] = None,
    retailer: Optional[str] = None,
    cli_override: Optional[str] = None
) -> ProxyClient
```

### get_with_retry()

```python
# Old signature
def get_with_retry(
    session: requests.Session,
    url: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    timeout: int = DEFAULT_TIMEOUT,
    ...
) -> Optional[requests.Response]

# New signature (backward compatible)
def get_with_retry(
    session: requests.Session,
    url: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    timeout: int = DEFAULT_TIMEOUT,
    retailer: Optional[str] = None,
    ...
) -> Optional[requests.Response]
```

## Proxy Mode Recommendations by Retailer

Based on existing comments in `retailers.yaml` and anti-bot complexity:

| Retailer | Recommended Mode | Reason |
|----------|------------------|--------|
| Verizon | `residential` | HTML crawl method, works well with proxies |
| AT&T | `direct` | Sitemap-based, low anti-bot measures |
| Target | `direct` | API-based, no proxy needed |
| T-Mobile | `direct` | Sitemap-based, straightforward |
| Walmart | `web_scraper_api` with `render_js: true` | Uses `__NEXT_DATA__`, benefits from JS rendering |
| Best Buy | `web_scraper_api` with `render_js: true` | Stronger anti-bot measures |

## Verification Approach

### Unit Testing
- Test configuration resolution priority with different combinations
- Test proxy client creation for different retailers
- Test configuration parsing from YAML

### Integration Testing
- Run single retailer with specific proxy mode
- Run multiple retailers with different proxy modes in sequence
- Verify proxy switching occurs correctly
- Test CLI override behavior

### Manual Verification
1. Test each retailer individually with its recommended proxy mode
2. Run `--all` with multiple retailers having different proxy configurations
3. Verify logs show correct proxy mode for each retailer
4. Test `--proxy` CLI override works across all retailers
5. Verify backward compatibility with existing environment variable setup

### Test Commands
```bash
# Test single retailer with default config
python run.py --retailer verizon --limit 5

# Test multiple retailers with different proxy modes
python run.py --all --limit 5

# Test CLI override
python run.py --all --proxy direct --limit 5

# Test backward compatibility (with PROXY_MODE env var)
export PROXY_MODE=direct
python run.py --retailer target --limit 5
```

## Edge Cases and Considerations

1. **Missing Retailer Config**: Fall back to global proxy config
2. **Invalid Proxy Mode**: Log warning and fall back to `direct`
3. **Missing Credentials**: Validate per mode, fail gracefully with clear error
4. **Concurrent Access**: Ensure thread-safe proxy client dictionary
5. **Memory Management**: Properly close all proxy clients on shutdown
6. **Error Isolation**: One retailer's proxy failure shouldn't affect others

## Backward Compatibility

- Existing environment variable configuration (`PROXY_MODE`) continues to work
- Existing CLI flag (`--proxy`) behavior unchanged (now acts as global override)
- Scrapers without `retailer` parameter default to global proxy client
- Empty or missing proxy sections in `retailers.yaml` use global defaults

## Success Criteria

1. ✅ Each retailer can have its own proxy mode in `retailers.yaml`
2. ✅ Multi-retailer runs automatically switch proxy modes per retailer
3. ✅ CLI `--proxy` flag overrides all retailer-specific settings
4. ✅ Existing environment variable and CLI workflows still work
5. ✅ No breaking changes to existing scraper APIs
6. ✅ All retailers run successfully with recommended proxy modes
7. ✅ Proper cleanup of all proxy clients on shutdown
