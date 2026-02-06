# Building production scraping systems with Oxylabs in Python

Oxylabs offers two fundamentally different product lines for web data collection: **Residential Proxies** (a pool of 175M+ real residential IPs you route your own HTTP requests through) and **Web Scraping API** (a managed service that handles proxies, retries, CAPTCHAs, and parsing for you). The right choice depends on how much control you need versus how much infrastructure you want to offload. Residential Proxies charge per GB of bandwidth consumed regardless of success, while the Web Scraping API charges only per successful result — a critical distinction for cost modeling. This guide covers everything a Python developer needs to architect, implement, and operate production-grade scraping systems on both products.

## Product architecture and how the two lines differ

**Residential Proxies** operate as a backconnect proxy gateway. You send requests through a single endpoint — `pr.oxylabs.io:7777` — and Oxylabs routes each request through a geographically distributed load balancer to one of  **175M+ residential IPs** across **195 countries**.  IPs are real addresses assigned by ISPs to physical devices.  By default, every request gets a new IP (automatic rotation).   You control targeting, sessions, and rotation via parameters embedded in the proxy username string. You handle all scraping logic, parsing, retries, and error handling yourself.

**Web Scraping API** is a fully managed scraping service.  You POST a JSON payload describing what you want (URL, source type, geo-location, whether to render JavaScript, whether to parse structured data), and Oxylabs returns the result.  Internally it uses ML-driven proxy selection, automatic retries, CAPTCHA bypassing, and headless browsers.  Three integration methods exist: **Realtime** (synchronous, 150-second TTL), **Push-Pull** (asynchronous with polling or webhooks, results stored 24 hours), and **Proxy Endpoint** (use the API as a traditional proxy on port 60000).   The Push-Pull method supports batch requests of up to **5,000 URLs per call**,  making it the best choice for high-volume pipelines.

### Authentication across both products

Residential Proxies support two authentication methods. **Username/password** requires prepending `customer-` to your sub-user username:  `http://customer-USERNAME:PASSWORD@pr.oxylabs.io:7777`.  **IP whitelisting** allows up to 10 IPv4 addresses in the dashboard, eliminating the need for credentials in requests — parameters are then passed via subdomain syntax like `cc-us-city-new_york.bc.pr.oxylabs.io:7777`.  The Web Scraping API uses standard **HTTP Basic Auth** with username and password passed in the Authorization header. 

### Protocols, pricing, and rate limits

Residential Proxies support **HTTP, HTTPS, and SOCKS5**   (SOCKS5 UDP is in beta).  Pricing is bandwidth-based: **$8/GB** on pay-as-you-go (frequently discounted to $4/GB), scaling down to roughly **$2/GB** on enterprise plans. All plans include unlimited concurrent sessions and free geo-targeting.  The Web Scraping API prices per successful result, varying by target complexity: **$0.50 per 1,000 Amazon results**, **$1.00 per 1,000 Google results**, and **$1.15–$1.35 per 1,000 results** for generic/JS-rendered pages. Rate limits on the API are **10 requests/second** on free trial and **50 requests/second** on paid plans  (upgradable by contacting support).

## Geographic targeting and session management

Oxylabs provides granular geo-targeting on Residential Proxies through username parameters, all at no extra cost.   The parameter hierarchy from most to least specific: **city > state > country**. Parameters are appended to the username string with hyphens.

```python
# Country targeting (ISO 3166-1 alpha-2)
proxy_user = "customer-USERNAME-cc-US"

# Country + city (multi-word cities use underscores)
proxy_user = "customer-USERNAME-cc-BR-city-rio_de_janeiro"

# State targeting
proxy_user = "customer-USERNAME-st-us_california"

# ASN targeting (mutually exclusive with country)
proxy_user = "customer-USERNAME-ASN-21928"

# ZIP/postal code
proxy_user = "customer-USERNAME-cc-US-postalcode-10001"
```

**Session management** defaults to rotating (new IP per request). For sticky sessions, append `sessid-{random_string}` to maintain the same IP  for up to **10 minutes** by default,   extendable to **24 hours** (1,440 minutes) using the `sesstime` parameter.   A critical detail: sessions expire after **60 seconds of inactivity** regardless of the configured duration.   Country-specific sticky entry nodes (e.g., `us-pr.oxylabs.io:10001-39999`) provide port-based sticky sessions capped at 10 minutes.  

```python
import random

session_id = random.randint(100000, 999999)
# Sticky session with country targeting, 30-minute duration
proxy_user = f"customer-USERNAME-cc-DE-sessid-{session_id}-sesstime-30"
proxy_url = f"http://{proxy_user}:PASSWORD@pr.oxylabs.io:7777"
```

For the Web Scraping API, geo-targeting is controlled via the `geo_location` parameter in the JSON payload, accepting country names, ISO codes, UULE values, coordinates with radius, and ZIP codes depending on the source type. 

## Python implementation with the official SDK and raw HTTP clients

### The official Oxylabs Python SDK

Oxylabs maintains an official SDK on PyPI: **`pip install oxylabs`**  (version 2.0.0+, Python 3.5+, MIT license).   It provides three client classes mapping to the three API integration methods:

```python
from oxylabs import RealtimeClient, AsyncClient, ProxyClient

# Synchronous / Realtime
client = RealtimeClient("username", "password")
result = client.google.scrape_search("adidas", parse=True, domain="com")
print(result.raw)

# Asynchronous / Push-Pull with polling
import asyncio

async def main():
    client = AsyncClient("username", "password")
    result = await client.amazon.scrape_product(
        "B07FZ8S74R",
        parse=True,
        timeout=45,      # Max seconds to wait for completion
        poll_interval=3   # Seconds between status checks
    )
    print(result.raw)

asyncio.run(main())

# Proxy Endpoint (use API as a proxy)
proxy = ProxyClient("username", "password")
proxy.add_geo_location_header("Germany")
proxy.add_render_header("html")  # Enable JS rendering
result = proxy.get("https://www.example.com")
```

The SDK supports all major sources including Google (search, ads, maps, shopping, trends, lens), Amazon (search, product, pricing, reviews, sellers, bestsellers), Bing, Walmart, eBay, Etsy, and a `universal` source for arbitrary URLs.  Custom parsing instructions using XPath/CSS selectors and browser instructions for headless automation are fully supported. 

### Residential Proxy integration with requests, aiohttp, and httpx

**Using `requests`** — the simplest integration path:

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import os

username = os.environ["OXYLABS_USERNAME"]
password = os.environ["OXYLABS_PASSWORD"]

# Production-grade session with connection pooling and retries
retry = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
adapter = HTTPAdapter(pool_connections=100, pool_maxsize=100, max_retries=retry)

session = requests.Session()
session.mount("https://", adapter)
session.mount("http://", adapter)
session.proxies = {
    "http": f"http://customer-{username}:{ password}@pr.oxylabs.io:7777",
    "https": f"http://customer-{username}:{password}@pr.oxylabs.io:7777",
}

response = session.get("https://example.com", timeout=(5, 30))
```

**Using `aiohttp`** — best for high-concurrency asyncio pipelines:

```python
import aiohttp
import asyncio

USER = os.environ["OXYLABS_USERNAME"]
PASS = os.environ["OXYLABS_PASSWORD"]
PROXY = f"http://customer-{USER}:{PASS}@pr.oxylabs.io:7777"

async def fetch(session, sem, url):
    async with sem:
        async with session.get(url, proxy=PROXY, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            return {"url": url, "status": resp.status, "body": await resp.text()}

async def scrape(urls, concurrency=20):
    sem = asyncio.Semaphore(concurrency)
    connector = aiohttp.TCPConnector(limit=concurrency, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch(session, sem, url) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=True)

results = asyncio.run(scrape(["https://example.com/page/1", "https://example.com/page/2"]))
```

**Using `httpx`** — modern async/sync dual-mode client:

```python
import httpx

proxy_url = f"https://customer-{USER}:{PASS}@pr.oxylabs.io:7777"

# Synchronous
with httpx.Client(proxy=proxy_url, timeout=30) as client:
    response = client.get("https://ip.oxylabs.io/")

# Asynchronous
async with httpx.AsyncClient(proxy=proxy_url, timeout=30) as client:
    response = await client.get("https://ip.oxylabs.io/")
```

### Web Scraping API integration patterns

For the API, the raw `requests` approach is straightforward and often sufficient:

```python
import requests

payload = {
    "source": "universal",
    "url": "https://example.com",
    "geo_location": "United States",
    "render": "html",           # Enable JS rendering
    "parse": True,              # Get structured JSON output
    "parsing_instructions": {   # Custom extraction rules
        "title": {"_fns": [{"_fn": "xpath_one", "_args": ["//title/text()"]}]},
        "price": {"_fns": [{"_fn": "css_one", "_args": [".price::text"]}]},
    },
}

response = requests.post(
    "https://realtime.oxylabs.io/v1/queries",
    auth=("USERNAME", "PASSWORD"),
    json=payload,
    timeout=180,  # Realtime TTL is 150s; set client timeout slightly higher
)
data = response.json()
```

For high-volume workloads, use the **Push-Pull batch endpoint** to submit up to 5,000 URLs in a single request,  then retrieve results via polling or webhook callbacks:

```python
batch_payload = {
    "source": "amazon_product",
    "query": ["B07FZ8S74R", "B08N5WRWNW", "B09V3KXJPB"],  # Up to 5,000
    "parse": True,
    "geo_location": "90210",
    "callback_url": "https://your-server.com/webhook",  # Optional
}

response = requests.post(
    "https://data.oxylabs.io/v1/queries/batch",
    auth=("USERNAME", "PASSWORD"),
    json=batch_payload,
)
jobs = response.json()  # Contains job IDs for each query
```

## Concurrency patterns and performance tuning

### Choosing the right concurrency model

Oxylabs Residential Proxies impose **no explicit concurrent connection limit** — all plans include unlimited concurrent sessions.   The Web Scraping API caps at **50 requests/second** on paid plans.   Given these constraints, the concurrency bottleneck is almost always the target site or your own infrastructure.

**`asyncio` with `aiohttp`** is the recommended approach for I/O-bound scraping workloads.  Oxylabs’ own tutorials demonstrate this pattern with `asyncio.Semaphore` controlling concurrency. Their benchmarks show asyncio outperforming threading for network-heavy tasks. Use `aiohttp.TCPConnector(limit=N)` for connection pooling combined with a semaphore for application-level concurrency control.

**`concurrent.futures.ThreadPoolExecutor`** works well for simpler pipelines or when integrating with synchronous libraries. Oxylabs’ testing showed **`max_workers=100`** completing 50 URLs in ~7 seconds versus 126 seconds sequentially, though the optimal worker count depends on your machine (32 workers was effective on their test hardware).

```python
from concurrent.futures import ThreadPoolExecutor
import requests

def scrape_url(url):
    proxies = {"http": proxy_url, "https": proxy_url}
    return requests.get(url, proxies=proxies, timeout=(5, 30))

with ThreadPoolExecutor(max_workers=50) as executor:
    results = list(executor.map(scrape_url, url_list))
```

### Optimal timeout and retry configuration

**Timeouts**: Set connection timeout to **5 seconds** and read timeout to **10–30 seconds** for proxy requests.   For Web Scraping API with JS rendering, increase the client timeout to **180 seconds** (the Realtime endpoint has a 150-second TTL).  Always use tuple format `timeout=(connect, read)` — Python’s `requests` library has no default timeout and will hang indefinitely without one. 

**Retries**: Use exponential backoff with jitter. Retry on **429, 500, 502, 503, 504**.   Do not retry 400 (fix your request), 401/407 (fix credentials), or 404 (resource doesn’t exist). Cap maximum delay at 180 seconds with a maximum of 5 retry attempts.

```python
from urllib3.util import Retry
import random

retry = Retry(
    total=5,
    backoff_factor=2,           # Delays: 2s, 4s, 8s, 16s, 32s
    status_forcelist=[403, 429, 500, 502, 503, 504],
    respect_retry_after_header=True,
)
# Add jitter to prevent thundering herd
# backoff_jitter parameter available in urllib3 >= 2.0
```

### Bandwidth optimization techniques

For Residential Proxies where you pay per GB, bandwidth optimization directly affects cost:

- **Enable compression**: Send `Accept-Encoding: gzip, deflate, br` headers to reduce response size by 60–80%
- **Use the `parse` parameter** on Web Scraping API to receive structured JSON instead of full HTML
- **Block unnecessary assets**: When using headless rendering, configure browser instructions to avoid loading images, CSS, and fonts
- **Deduplicate URLs** before scraping to avoid redundant requests
- **Cache responses**: Use a local cache layer (Redis, SQLite) to avoid re-fetching unchanged pages 
- **Selective parsing**: Extract only needed fields server-side using `parsing_instructions` with XPath/CSS selectors 

## Designing a resilient scraping pipeline

### Queue-based architecture with Celery and Redis

For production systems processing thousands to millions of URLs, a queue-based architecture separates concerns cleanly:

```
FastAPI (Job Submission) → Redis Broker → Celery Workers → Oxylabs → PostgreSQL/S3
       ↓                                       ↓
  Job Status API                         Flower Monitoring
```

Key design principles for this architecture:

- **Never store large payloads in Redis**. Stream HTML/data directly to S3 or your database from workers. Return only reference keys (S3 key, database ID) as Celery task results, or use `ignore_result=True` for pure data pipelines. 
- **Domain-specific task queues** with different rate limits. A target like Amazon might tolerate 20 concurrent requests while a smaller site might need throttling to 2 requests/second.
- **Circuit breakers** per target domain: after N consecutive failures, pause requests for a cooldown period rather than burning bandwidth on a temporarily blocked target.
- **Dead letter queues** for URLs that fail after max retries — send them to a separate queue for manual review rather than retrying indefinitely.
- **Deduplication** via Redis Sets or Bloom filters to prevent processing the same URL twice.

Alternatively, leverage Oxylabs’ **native Push-Pull infrastructure** as your queue system: submit batch jobs of up to 5,000 URLs,  configure webhook callbacks for completion notifications, and optionally upload results directly to **AWS S3, Google Cloud Storage, or Alibaba Cloud OSS**  — eliminating the need to manage Celery workers entirely.

### When to choose Web Scraping API versus Residential Proxies

|Factor              |Web Scraping API                         |Residential Proxies                                    |
|--------------------|-----------------------------------------|-------------------------------------------------------|
|Engineering effort  |Low — single API call                    |High — full scraper stack                              |
|Anti-bot handling   |Automatic (CAPTCHAs, fingerprinting)     |Manual implementation                                  |
|Cost model          |Per successful result only               |Per GB regardless of outcome                           |
|Billing for failures|Not charged for 5xx/6xx                  |Charged for all bandwidth                              |
|JavaScript rendering|Built-in (`render: "html"`)              |Requires your own headless browser                     |
|Best for            |SERP/e-commerce scraping, structured data|Custom scrapers, multi-step flows, real-time monitoring|
|Scaling mechanism   |Push-Pull batch (5,000 URLs/request)     |Celery/Redis worker pools                              |

**Use the Web Scraping API** when you need structured data from supported sources (Google, Amazon, Walmart, etc.), when anti-bot complexity is high, or when you want to minimize engineering investment. **Use Residential Proxies** when you need full control over request headers, timing, and scraping logic, when targets aren’t covered by the API’s built-in sources, or when building complex multi-step workflows with session persistence.

## Error handling, monitoring, and security

### Error codes and what to do about them

Residential Proxies include an **`X-Error-Description` response header** on infrastructure errors — always log this value.   Key error patterns: **502 with “Exit node not found”** means the session ended or no IP matches your ASN filter — start a new session.  **407** on first use of new credentials — change the password in the dashboard and retry.  **504** indicates a timeout reaching the target — retry with backoff. 

The Web Scraping API uses a richer status code system.  Parser-specific codes (**12000–12009**) indicate parsing outcomes:  **12000** is full success, **12004** is partial success with some missing fields, **12002** means the HTML structure changed and the parser broke. Cloud storage upload codes (**13000–13103**) and session codes (**15001–15003**) cover their respective subsystems.  The critical billing rule: **you are not charged for 5xx or 6xx responses** from the Web Scraping API.  

### Monitoring and observability

The Oxylabs dashboard at `dashboard.oxylabs.io` provides usage statistics, daily bandwidth breakdowns, and per-user tracking.   The **Public API** at `https://residential-api.oxylabs.io/v2` enables programmatic access to traffic stats.   For production systems, supplement this with application-level monitoring: track success rates per domain, log all error codes and `X-Error-Description` values, alert on success rate drops below your threshold (e.g., 95%), and monitor bandwidth consumption trends against your plan limits. Oxylabs publishes infrastructure status at `uptime.oxylabs.io`.

### Credential security

Never hardcode Oxylabs credentials. Environment variables are the minimum baseline — use `os.environ["OXYLABS_USERNAME"]` with `.env` files protected by `.gitignore` for development.  For production, use a secrets manager (AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager).  In Kubernetes, prefer volume-mounted secrets over environment variables, as env vars are visible in pod specs.  Rotate credentials every 30–90 days.  Use separate proxy sub-users per environment (dev, staging, production) and set per-user traffic limits via the dashboard to prevent runaway costs.  Run pre-commit hooks with tools like `git-secrets` to catch accidentally committed credentials. 

## Conclusion: key architectural decisions

The most impactful decision is **product selection**. If your targets are covered by the Web Scraping API’s built-in sources (Google, Amazon, and dozens of e-commerce sites), start there — the managed retries, CAPTCHA handling, and per-success billing model dramatically reduce both engineering effort and wasted spend. For everything else, Residential Proxies with `asyncio`/`aiohttp` and a semaphore-controlled concurrency pattern provide the best throughput-to-cost ratio.

Three patterns deserve emphasis. First, **always use the `parse` parameter** on the Web Scraping API — it returns structured JSON instead of raw HTML,   reducing both bandwidth and post-processing code. Second, **Push-Pull batch mode** is underutilized: submitting 5,000 URLs in a single HTTP call  with webhook callbacks or direct S3 upload   replaces an entire Celery pipeline for many use cases. Third, **sticky sessions are misunderstood** — the 60-second inactivity timeout means you must keep sessions warm with periodic requests during multi-step flows, regardless of the configured `sesstime` duration.   Building with these patterns from the start avoids the most common production pitfalls.