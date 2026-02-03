---
name: proxy-tester
description: Tests Oxylabs proxy configuration and diagnoses connectivity issues
---

# Proxy Tester Agent

Tests Oxylabs proxy configuration and diagnoses connectivity issues.

## When to Use

- Before running scrapers with proxy mode
- When scrapers fail with connection errors
- To verify proxy credentials are working
- To diagnose rate limiting issues

## Test Sequence

### 1. Verify Credentials

Check that environment variables are set (values hidden for security):

```bash
# Check environment variables exist
env | grep -E "OXYLABS_|PROXY_" | sed 's/=.*/=***/'
```

### 2. Test Residential Proxy

```python
from src.shared.proxy_client import ProxyClient, ProxyMode
import os

# Check credentials exist
username = os.getenv('OXYLABS_RESIDENTIAL_USERNAME') or os.getenv('OXYLABS_USERNAME')
password = os.getenv('OXYLABS_RESIDENTIAL_PASSWORD') or os.getenv('OXYLABS_PASSWORD')

if not username or not password:
    print("ERROR: Missing proxy credentials")
    print("Set OXYLABS_RESIDENTIAL_USERNAME and OXYLABS_RESIDENTIAL_PASSWORD")
else:
    client = ProxyClient(ProxyMode.RESIDENTIAL)
    result = client.test_connection()
    print(f"Connection test: {result}")
```

### 3. Test Web Scraper API

```python
from src.shared.proxy_client import ProxyClient, ProxyMode
import os

username = os.getenv('OXYLABS_SCRAPER_API_USERNAME') or os.getenv('OXYLABS_USERNAME')
password = os.getenv('OXYLABS_SCRAPER_API_PASSWORD') or os.getenv('OXYLABS_PASSWORD')

if not username or not password:
    print("ERROR: Missing scraper API credentials")
else:
    client = ProxyClient(ProxyMode.WEB_SCRAPER_API)
    result = client.test_connection()
    print(f"Connection test: {result}")
```

### 4. Test with Specific Retailer

```bash
# Test residential proxy with a single store
python run.py --retailer verizon --proxy residential --validate-proxy --test --limit 1

# Test web scraper API with JS rendering
python run.py --retailer walmart --proxy web_scraper_api --render-js --test --limit 1
```

### 5. Check for Rate Limiting

Look for 429 errors in output and verify delay configuration:

```bash
# Check delay configuration for a retailer
grep -A 20 "^  verizon:" config/retailers.yaml | grep -A 10 "delays:"
```

## Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| Missing credentials | `ProxyAuthenticationRequired` | Set `OXYLABS_*` env vars |
| Wrong proxy mode | Connection refused | Match proxy mode to retailer needs |
| Rate limiting | 429 Too Many Requests | Increase delays in `retailers.yaml` |
| Geo-blocking | 403 Forbidden | Use geo-targeted proxy (`--proxy-country`) |
| JS not rendered | Missing dynamic content | Use `--proxy web_scraper_api --render-js` |

## Environment Variable Reference

```bash
# Residential proxy (rotating IPs)
OXYLABS_RESIDENTIAL_USERNAME=your_username
OXYLABS_RESIDENTIAL_PASSWORD=your_password

# Web Scraper API (managed service)
OXYLABS_SCRAPER_API_USERNAME=your_username
OXYLABS_SCRAPER_API_PASSWORD=your_password

# Fallback (used if specific vars not set)
OXYLABS_USERNAME=your_username
OXYLABS_PASSWORD=your_password
```

## Delay Configuration

For proxied requests, you can use more aggressive delays:

```yaml
# In config/retailers.yaml
retailers:
  verizon:
    delays:
      direct:      # Conservative (no proxy)
        min_delay: 2.0
        max_delay: 5.0
      proxied:     # Aggressive (with proxy)
        min_delay: 0.2
        max_delay: 0.5
```
