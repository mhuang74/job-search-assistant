# Indeed Kameleo Scraper - Usage Guide

## Overview

The `IndeedKameleoScraper` is an advanced web scraper that uses Playwright with Kameleo browser profiles to bypass Indeed's bot detection. Kameleo provides real browser fingerprints and better protection against detection compared to standard Playwright stealth techniques.

## Prerequisites

### 1. Install Kameleo CLI

Download and install Kameleo from: https://www.kameleo.io/

Start the Kameleo CLI before running the scraper:
```bash
# Kameleo should be running on localhost:5050 (default port)
```

### 2. Install Python Dependencies

```bash
# Install all dependencies including Kameleo
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 3. Environment Variables (Optional)

```bash
# Set Kameleo port (default: 5050)
export KAMELEO_PORT=5050

# Set proxy if needed
export HTTPS_PROXY=http://username:password@proxy.example.com:8080
```

## Basic Usage

### Simple Search

```python
import asyncio
from src.scrapers.indeed_kameleo import IndeedKameleoScraper

async def main():
    async with IndeedKameleoScraper() as scraper:
        jobs = await scraper.search(
            query='technical product manager',
            location='Remote',
            max_results=50
        )

        for job in jobs:
            print(f"{job.title} at {job.company}")
            print(f"  URL: {job.url}")
            if job.company_website:
                print(f"  Website: {job.company_website}")

asyncio.run(main())
```

### With Configuration

```python
import asyncio
from src.scrapers.indeed_kameleo import IndeedKameleoScraper

async def main():
    # Configure scraper with proxy
    config = {
        'proxy': 'http://user:pass@proxy.example.com:8080',
        'kameleo_port': 5050,  # Default port
    }

    async with IndeedKameleoScraper(config) as scraper:
        jobs = await scraper.search(
            query='software engineer',
            location='San Francisco, CA',
            max_results=100,
            remote_only=False
        )

        print(f"Found {len(jobs)} jobs")

asyncio.run(main())
```

## Configuration Options

### Scraper Configuration

Pass these options in the `config` dictionary:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `proxy` | str | None | Proxy URL in format: `http://user:pass@host:port` |
| `kameleo_port` | int | 5050 | Port where Kameleo CLI is running |

### Search Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | str | Required | Job search query (e.g., "technical product manager") |
| `location` | str | "Remote" | Location filter |
| `max_results` | int | 50 | Maximum number of jobs to return |
| `remote_only` | bool | True | Filter for remote jobs only |

## Features

### Anti-Detection

- **Real Browser Fingerprints**: Uses Kameleo's macOS Chrome desktop fingerprints
- **CDP Connection**: Connects via Chrome DevTools Protocol for better stealth
- **Profile Management**: Automatic creation, start, and cleanup of browser profiles
- **Proxy Support**: Built-in proxy configuration for IP rotation

### Data Extraction

- **Job Details**: Title, company, location, description, URL, posted date
- **Company Websites**: Automatically extracts company websites from company pages
- **Smart Caching**: Caches company website lookups to avoid duplicate fetches
- **Error Handling**: Comprehensive error handling with retry logic

### Logging

The scraper provides detailed logging for debugging:

```python
from loguru import logger

# Configure logging
logger.add("scraper.log", rotation="1 MB", level="DEBUG")
```

## Running the Test Script

Use the included test script to verify everything works:

```bash
python test_indeed_kameleo.py
```

The test script will:
1. Initialize Kameleo profile
2. Search for "technical product manager" jobs
3. Extract company websites
4. Display results with statistics
5. Clean up Kameleo profile

## Error Handling

### Common Errors

#### Kameleo Not Running

```
❌ Failed to connect to Kameleo Local API at http://localhost:5050
```

**Solution**: Start Kameleo CLI before running the scraper

#### No Fingerprints Found

```
❌ No suitable fingerprints found in Kameleo
```

**Solution**: Ensure Kameleo has fingerprints available. The scraper will fallback to any desktop Chrome fingerprint if macOS fingerprints aren't available.

#### CAPTCHA Detected

```
❌ CAPTCHA detected on Indeed page!
```

**Solution**:
- Use a residential proxy
- Add more random delays between requests
- Wait before retrying
- Consider implementing a CAPTCHA solver (future enhancement)

#### Rate Limited (429)

```
❌ Indeed returned 429 Too Many Requests - rate limited
```

**Solution**: Wait a few minutes before trying again

#### Blocked (403)

```
❌ Indeed returned 403 Forbidden - likely blocked
```

**Solution**:
- Use a different proxy or IP address
- Wait 15-30 minutes before retrying
- Ensure Kameleo is using fresh fingerprints

## Advanced Usage

### Using with Proxy Rotation

```python
import asyncio
from src.scrapers.indeed_kameleo import IndeedKameleoScraper

async def search_with_proxy_rotation():
    proxies = [
        'http://user:pass@proxy1.example.com:8080',
        'http://user:pass@proxy2.example.com:8080',
        'http://user:pass@proxy3.example.com:8080',
    ]

    all_jobs = []

    for proxy in proxies:
        config = {'proxy': proxy}

        async with IndeedKameleoScraper(config) as scraper:
            jobs = await scraper.search(
                query='data scientist',
                location='Remote',
                max_results=50
            )
            all_jobs.extend(jobs)

    print(f"Total jobs collected: {len(all_jobs)}")

asyncio.run(search_with_proxy_rotation())
```

### Batch Processing

```python
import asyncio
from src.scrapers.indeed_kameleo import IndeedKameleoScraper

async def batch_search():
    queries = [
        'technical product manager',
        'senior product manager',
        'director of product',
    ]

    async with IndeedKameleoScraper() as scraper:
        for query in queries:
            print(f"\nSearching: {query}")
            jobs = await scraper.search(query=query, max_results=20)
            print(f"Found {len(jobs)} jobs for '{query}'")

            # Add delay between queries
            await asyncio.sleep(10)

asyncio.run(batch_search())
```

## Performance

### Expected Performance

- **Speed**: ~50 jobs in under 3 minutes (with delays)
- **Success Rate**: High, with Kameleo's anti-detection
- **CAPTCHA Rate**: Low with proper proxy and delays

### Optimization Tips

1. **Use Residential Proxies**: Better success rate than datacenter proxies
2. **Add Delays**: Use 5-10 second delays between pages
3. **Batch Wisely**: Don't scrape too many pages in one session
4. **Monitor Logs**: Watch for blocking indicators in logs

## Troubleshooting

### Debug Mode

Run with verbose logging to see what's happening:

```python
from loguru import logger
logger.add("debug.log", level="DEBUG")
```

### Save Debug Files

When errors occur, the scraper automatically saves:
- `debug_indeed_page_{page_num}.html` - Page HTML for inspection
- `debug_indeed_captcha_{page_num}.html` - CAPTCHA page HTML
- `debug_indeed_error_page_{page_num}.png` - Screenshot of error page

### Check Kameleo Connection

```python
import asyncio
from kameleo.local_api_client import ClientBuilder

async def test_kameleo():
    try:
        client = ClientBuilder("http://localhost:5050").build()
        print("✅ Kameleo is running!")
    except Exception as e:
        print(f"❌ Kameleo connection failed: {e}")

asyncio.run(test_kameleo())
```

## Comparison with IndeedPlaywrightScraper

### Advantages of Kameleo Scraper

- **Better Anti-Detection**: Real browser fingerprints vs. spoofed headers
- **Higher Success Rate**: Lower CAPTCHA and blocking rates
- **Professional Tool**: Kameleo is designed for web scraping at scale
- **Easier Maintenance**: No need to update stealth scripts manually

### When to Use Each

**Use Kameleo Scraper when:**
- You need better anti-detection
- You're getting blocked frequently
- You're scraping at scale
- You have Kameleo license

**Use Playwright Scraper when:**
- You don't have Kameleo installed
- Quick one-off searches
- Testing/development
- Budget constraints

## Future Enhancements

Planned improvements:

1. **Fingerprint Rotation**: Rotate between multiple fingerprints
2. **Session Management**: Reuse profiles across searches
3. **CAPTCHA Solver**: Automatic CAPTCHA solving
4. **Profile Pooling**: Pool of warm profiles for faster startup
5. **Metrics Collection**: Track success rates and performance

## Support

For issues or questions:

1. Check the logs for error messages
2. Review the debug files generated
3. Ensure Kameleo is running and accessible
4. Try with a different proxy or IP address
5. Open an issue with detailed error logs

## References

- [Kameleo Documentation](https://app.kameleo.io/api-reference)
- [Kameleo Python Examples](https://github.com/kameleo-io/local-api-examples/tree/master/python)
- [Playwright Documentation](https://playwright.dev/python/)
