# Indeed Pagination Research: Why Residential Proxies Alone Aren't Enough

**Date**: November 2025
**Issue**: Pagination blocked beyond first page despite residential proxy usage

## Executive Summary

Indeed has implemented sophisticated multi-layered anti-bot protection that goes beyond simple IP-based blocking. Residential proxies alone are insufficient because Indeed uses **behavioral analysis**, **browser fingerprinting**, **TLS fingerprinting**, and **Cloudflare's anti-bot system** to detect and block automated scrapers.

## Indeed's Anti-Scraping Measures

### 1. Cloudflare Protection
Indeed is protected by Cloudflare's anti-bot system, which includes:
- "Verify you are human" challenges
- Turnstile CAPTCHA (Cloudflare's CAPTCHA replacement since 2022)
- Per-customer machine learning models that tune detection based on traffic patterns
- Browser fingerprinting analyzing user-agent strings, screen resolution, and installed plugins

### 2. TLS Fingerprinting
Indeed's server detects non-browser traffic through TLS signatures. Standard HTTP clients (requests, httpx) return **403 Forbidden** because their TLS fingerprints don't match real browsers. This is why proxies alone don't work—the connection itself is detected as automated.

### 3. Behavioral Detection
- Request patterns (too fast, too consistent)
- Navigator properties (`navigator.webdriver = true` in Selenium)
- JavaScript execution patterns
- Absence of human-like mouse movements and interactions

### 4. Rate Limiting
- IP-based rate limiting triggers after repeated access
- Session-based tracking across pagination requests
- CSRF token validation in JSON data structures

## Why Current Implementation Fails on Pagination

Based on codebase analysis (`src/scrapers/indeed.py`):

### Current Approach Issues:
1. **Playwright with basic stealth** - Not sufficient against Cloudflare Turnstile
2. **Static fingerprinting** - Same browser fingerprint across pagination requests
3. **Predictable timing** - Even with random delays (5-10s), patterns are detectable
4. **Offset mismatch** - Code assumes 15 jobs/page but uses `start=page_num * 10`
5. **No reconnection strategy** - Selenium/Playwright maintain continuous connection

### Key Problem:
Cloudflare tracks the browser session. After the first page loads successfully, subsequent navigation (pagination) can trigger additional verification because:
- The session shows automated behavior patterns
- The WebDriver connection is detectable during navigation
- Request timing patterns are analyzed

## Proposed Solutions

### Solution 1: SeleniumBase UC Mode (Recommended)

SeleniumBase's Undetected Chrome (UC) mode specifically handles Cloudflare bypass:

```python
from seleniumbase import SB

with SB(uc=True, headless=False) as sb:
    # Use uc_open_with_reconnect to disconnect chromedriver before page loads
    sb.uc_open_with_reconnect(url, reconnect_time=5)

    # For pagination clicks, use uc_click to schedule click while disconnected
    sb.uc_click(pagination_selector)
```

**Key Features:**
- Disconnects chromedriver during page loads (undetectable during Cloudflare check)
- `uc_gui_click_captcha()` can attempt to solve CAPTCHAs automatically
- Automatic chromedriver version matching
- Built-in stealth against detection

**Limitations:**
- Requires GUI mode for CAPTCHA solving
- Slower than headless approaches

### Solution 2: Extract from Embedded JSON (Most Reliable)

Instead of navigating pages, extract pagination data from the embedded JSON:

```python
import re
import json

# Pattern to extract mosaic data
MOSAIC_PATTERN = r'window\.mosaic\.providerData\["mosaic-provider-jobcards"\]\s*=\s*({.*?});'

def extract_jobs(html):
    match = re.search(MOSAIC_PATTERN, html)
    if match:
        data = json.loads(match.group(1))
        jobs = data['metaData']['mosaicProviderJobCardsModel']['results']

        # Get total count for pagination planning
        tier_summaries = data['metaData']['mosaicProviderJobCardsModel']['tierSummaries']
        total_jobs = sum(tier['jobCount'] for tier in tier_summaries)

        return jobs, total_jobs
```

**Benefits:**
- More stable than DOM parsing (selectors change frequently)
- Contains richer data (salary, ratings, etc.)
- Pagination info included in the response

### Solution 3: Fresh Browser Context Per Page

Create new browser context for each pagination request:

```python
async def scrape_with_fresh_context(self, urls):
    results = []
    for url in urls:
        # New context = new fingerprint = harder to track
        context = await self.browser.new_context(
            viewport={'width': random.randint(1024, 1920),
                      'height': random.randint(768, 1080)},
            user_agent=self._get_random_ua()
        )
        page = await context.new_page()

        try:
            await page.goto(url)
            results.append(await self._extract_jobs(page))
        finally:
            await context.close()

        await asyncio.sleep(random.uniform(10, 20))  # Longer delays

    return results
```

### Solution 4: FlareSolverr Integration

Use FlareSolverr as a proxy service to handle Cloudflare challenges:

```python
# FlareSolverr running on localhost:8191
def get_page_via_flaresolverr(url):
    payload = {
        "cmd": "request.get",
        "url": url,
        "maxTimeout": 60000
    }
    response = requests.post(
        "http://localhost:8191/v1",
        json=payload
    )
    return response.json()["solution"]["response"]
```

**Setup:**
```bash
docker run -d \
  --name=flaresolverr \
  -p 8191:8191 \
  ghcr.io/flaresolverr/flaresolverr:latest
```

### Solution 5: Web Scraping API Services

For production reliability, consider commercial solutions:
- **ScrapeOps** - Proxy aggregator with anti-bot bypass
- **ScrapFly** - Handles Cloudflare automatically
- **Bright Data** - Residential proxies with built-in unlocker
- **Decodo/Oxylabs** - Web Scraper API with JS rendering

```python
# Example with ScrapeOps
def scrapeops_url(url):
    payload = {
        'api_key': SCRAPEOPS_API_KEY,
        'url': url,
        'country': 'us',
        'render_js': True
    }
    return 'https://proxy.scrapeops.io/v1/?' + urlencode(payload)
```

## Implementation Recommendations

### Immediate Fixes:

1. **Switch to SeleniumBase UC mode** instead of Playwright
2. **Extract from mosaic JSON** instead of parsing HTML
3. **Increase delays** to 15-30 seconds between pages
4. **Randomize everything** - viewport, UA, timezone per request

### Code Changes Required:

```python
# Current (indeed.py line 255-264)
params = {
    'q': query,
    'l': location,
    'start': page_num * 10,  # Indeed actually uses increments of 10
}

# Recommended additions:
# 1. Add random parameters to vary fingerprint
params['ts'] = int(time.time() * 1000)  # Timestamp to prevent caching
params['vjk'] = generate_random_id()     # View job key variation
```

### Session Management:

```python
# Rotate browser contexts
async def rotate_context(self):
    if self.request_count % 3 == 0:  # Every 3 requests
        await self.context.close()
        self.context = await self.browser.new_context(...)
        self.request_count = 0
```

## Testing Checklist

- [ ] Test with SeleniumBase UC mode
- [ ] Verify mosaic JSON extraction works across pages
- [ ] Test pagination with fresh contexts
- [ ] Measure success rate with different delay intervals
- [ ] Test FlareSolverr integration
- [ ] Compare residential vs datacenter proxy success rates

## Sources

1. Decodo Blog - "How to Scrape Indeed: Step-by-Step Guide" (2025)
2. ScrapeOps - "How To Scrape Indeed.com with Python and Selenium" (2025)
3. Oxylabs Blog - "How to Scrape Indeed Jobs Data in 2025"
4. SeleniumBase Documentation - UC Mode
5. GitHub - undetected-chromedriver project
6. ZenRows - "How to Bypass Cloudflare in 2025"
7. Bright Data - "Handling Pagination While Web Scraping in 2025"

## Conclusion

The root cause of pagination failure is not the proxy itself, but **browser fingerprint consistency** and **Cloudflare's behavioral detection** across page requests. The solution requires:

1. Disconnecting the automation driver during critical moments (UC mode)
2. Varying browser fingerprints between requests
3. Extracting data from embedded JSON rather than navigating DOM
4. Using longer, more randomized delays
5. Consider fresh browser contexts per pagination request

Residential proxies are necessary but not sufficient—they must be combined with anti-detection browser automation techniques.
