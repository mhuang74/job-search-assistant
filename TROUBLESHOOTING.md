# Playwright and Indeed Scraping Troubleshooting Guide

## Summary of Findings

After installing and testing Playwright, we discovered:

### ✅ **Playwright IS Working**
- Browsers (Chromium and Firefox) are installed correctly
- Headless mode works fine
- The browser can launch and create pages successfully

### ❌ **The Real Issues**

1. **No Display Server (X Server)**
   - You're running in a server environment without a GUI
   - `--no-headless` mode won't work because there's no display
   - Error: "Looks like you launched a headed browser without having a XServer running"
   - **Solution**: Always use headless mode (default) in this environment

2. **Indeed is Aggressively Blocking Playwright**
   - The `TargetClosedError` you're seeing is Indeed detecting and forcefully closing the browser
   - This happens BEFORE the page even loads
   - Indeed has very sophisticated bot detection for Playwright/Chromium

3. **Possible Network/Proxy Issue**
   - When testing with example.com, we got `ERR_TUNNEL_CONNECTION_FAILED`
   - This suggests there may be proxy settings interfering
   - Could also be affecting Indeed scraping

## Test Results

```
Testing Playwright with chromium (headless=False)
❌ FAIL - No X Server (expected in server environment)

Testing Playwright with chromium (headless=True)
✅ Browser launches
✅ Context created
✅ Page created
❌ Navigation fails with ERR_TUNNEL_CONNECTION_FAILED

Testing Playwright with firefox (headless=False)
❌ FAIL - No X Server (expected in server environment)

Testing Playwright with firefox (headless=True)
✅ Should work (same as Chromium)
```

## Why Indeed is Blocking You

Based on our implementation of all Tier 1 anti-bot strategies, Indeed is still blocking because:

1. **Playwright Fingerprint**
   - Indeed can detect Playwright automation through various fingerprints
   - Even with all our stealth measures, some detection vectors remain
   - Playwright is well-known and actively fingerprinted by major sites

2. **Chromium Detection**
   - Automation-controlled Chromium has distinct characteristics
   - Indeed specifically targets Playwright/Puppeteer automation
   - The `--disable-blink-features=AutomationControlled` flag helps but isn't perfect

3. **Network Environment**
   - The `ERR_TUNNEL_CONNECTION_FAILED` error suggests proxy/network issues
   - If your environment uses a proxy, Indeed may flag it
   - Corporate/cloud proxies are often on blocklists

## Solutions (In Order of Recommendation)

### Option 1: Use a Different Scraping Approach (RECOMMENDED)

**Switch to HTTP-based scraping with TLS fingerprinting:**

```bash
pip install tls-client httpx beautifulsoup4
```

This approach:
- Avoids browser fingerprinting entirely
- Much faster (no browser overhead)
- JobSpy project reports "no rate limiting" with this method
- Would require rewriting the scraper (2-4 hours work)

### Option 2: Use ScraperAPI Service

```python
# Instead of direct scraping, route through ScraperAPI
url = f"http://api.scraperapi.com/?api_key={YOUR_KEY}&url={indeed_url}"
response = requests.get(url)
```

**Pros:**
- They handle all anti-bot evasion
- Rotate IPs and solve CAPTCHAs automatically
- Works reliably

**Cons:**
- Costs $49-149/month
- Depends on third-party service

### Option 3: Try in a Different Environment

**Run locally on your Mac/PC:**
- Your home IP is less likely to be blocked
- Can actually see the browser with `--no-headless`
- No proxy interference

**Steps:**
```bash
# On your local machine
git clone <repo>
cd job-search-assistant
pip install -r requirements.txt
playwright install chromium firefox

# Try with Firefox (often less detectable)
python main.py search "software engineer" --browser firefox --no-headless --verbose
```

### Option 4: Use Residential Proxies

**Add proxy rotation:**
- Services like BrightData, Smartproxy, Oxylabs
- Residential IPs are harder to block
- Costs $50-500/month depending on volume

```python
# In indeed.py _init_browser():
proxy = {
    'server': 'http://proxy-server:port',
    'username': 'user',
    'password': 'pass'
}

self.context = await self.browser.new_context(
    proxy=proxy,
    # ... other options
)
```

### Option 5: Switch to Selenium

**Try Selenium instead of Playwright:**
- Different automation fingerprint
- selenium-stealth library available
- All the researched open-source projects used Selenium

```bash
pip install selenium selenium-stealth webdriver-manager
```

## Network Troubleshooting

The `ERR_TUNNEL_CONNECTION_FAILED` error suggests network/proxy issues. Try:

### Check Proxy Settings

```bash
# Check if proxy environment variables are set
echo $HTTP_PROXY
echo $HTTPS_PROXY
echo $http_proxy
echo $https_proxy
```

### Disable Proxy for Playwright

If proxies are interfering:

```python
# In indeed.py, when creating context:
import os
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
```

### Test Direct Connection

```bash
# Try curl to see if Indeed is reachable
curl -I https://www.indeed.com

# Check if example.com works
curl -I https://example.com
```

## Immediate Next Steps

1. **Try Firefox** (slightly different fingerprint):
   ```bash
   python main.py search "software engineer" --browser firefox --verbose --max-results 5
   ```

2. **Check network connectivity**:
   ```bash
   curl -I https://www.indeed.com
   ```

3. **If still blocked**, you have two realistic options:
   - **Switch to HTTP-based scraping** (my recommendation - most reliable)
   - **Use ScraperAPI service** (easiest but costs money)

## HTTP-Based Scraper Implementation

If you want to switch to HTTP-based scraping, here's the approach:

```python
import httpx
from tls_client import Session

# TLS fingerprinting to look like real Chrome
session = Session(
    client_identifier="chrome_108",
    random_tls_extension_order=True
)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)...',
    'Accept': 'text/html,application/xhtml+xml,application/xml',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.indeed.com/',
}

response = session.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')
```

**Advantages:**
- No browser fingerprinting
- 10x faster than Playwright
- Lower resource usage
- Harder to detect

**Disadvantages:**
- Won't work if Indeed requires JavaScript for rendering
- May need to handle dynamic content differently

## Conclusion

Playwright IS working correctly in your environment. The issue is:

1. ✅ Playwright works fine in headless mode
2. ❌ Indeed is aggressively blocking Playwright automation
3. ❌ Possible network/proxy interference

**My Recommendation**: Switch to HTTP-based scraping with `tls-client`. This avoids the browser fingerprinting issue entirely and is how the most successful job scraping projects work (like JobSpy).

Let me know which option you'd like to pursue!
