# Indeed Kameleo Scraper - Implementation Specification

## Overview
Create a new Indeed.com scraper using Playwright with Kameleo browser profiles for enhanced anti-detection capabilities. Kameleo provides real browser fingerprints and better protection against bot detection compared to standard Playwright stealth techniques.

## Objectives
- Leverage Kameleo's browser fingerprinting to bypass Indeed's bot detection
- Support proxy configuration for IP rotation
- Use Chrome browser on desktop macOS configuration
- Search for jobs (default query: 'technical product manager')
- Maintain compatibility with existing BaseScraper interface

## Architecture

### Class Structure
```python
class IndeedKameleoScraper(BaseScraper):
    """Indeed scraper using Playwright with Kameleo browser profiles"""
```

### Key Dependencies
- `kameleo-local-api-client` - Kameleo API client
- `playwright` - Browser automation
- Existing `BaseScraper` base class
- Existing `JobListing` and `JobBoard` models

## Technical Requirements

### 1. Kameleo Integration

#### Profile Creation
- **Device Type**: `desktop`
- **Browser Product**: `chrome`
- **Operating System**: Filter for macOS fingerprints
- **Profile Naming**: Use descriptive names like `"Indeed Scraper - {timestamp}"`

#### Connection Method
- Use Playwright's CDP (Chrome DevTools Protocol) connection
- Connect via WebSocket endpoint: `ws://localhost:{kameleo_port}/playwright/{profile.id}`
- Leverage Kameleo's existing browser context (don't create new context)

### 2. Proxy Support

#### Configuration
- Accept proxy via config dict parameter: `config['proxy']`
- Support environment variables: `HTTPS_PROXY`, `HTTP_PROXY` as fallback
- Proxy format: `http://username:password@host:port`

#### Implementation
```python
# Set proxy in Kameleo profile creation request
create_profile_request = CreateProfileRequest(
    fingerprint_id=fingerprint.id,
    name='Indeed Scraper',
    proxy=proxy_config  # If provided
)
```

### 3. Browser Configuration

#### Base Settings
- **Browser**: Chrome
- **Device**: Desktop
- **Platform**: macOS (filter fingerprints by OS)
- **Kameleo Port**: Default `5050`, override via `KAMELEO_PORT` env var

#### Search Fingerprints
```python
fingerprints = client.fingerprint.search_fingerprints(
    device_type='desktop',
    browser_product='chrome',
    os_family='macos'  # Filter for macOS fingerprints
)
```

### 4. Search Functionality

#### Default Parameters
- **Query**: 'technical product manager'
- **Location**: 'Remote' (configurable)
- **Max Results**: 50 (configurable)
- **Remote Only**: True (configurable)

#### Implementation Approach
- Reuse existing `_scrape_page()` logic from `IndeedPlaywrightScraper`
- Reuse existing `_parse_job_card()` parsing logic
- Adapt browser initialization to use Kameleo profiles
- Maintain pagination support (Indeed shows ~15 jobs per page)

## Implementation Details

### File Structure
```
src/scrapers/indeed_kameleo.py  # New file
```

### Class Methods

#### `__init__(self, config: dict = None)`
- Initialize BaseScraper
- Store Kameleo client reference
- Initialize profile tracking

#### `async __aenter__(self)` / `__aexit__(self)`
- Async context manager support
- Handle profile lifecycle (create, start, stop)

#### `async _init_browser(self)`
1. Connect to Kameleo Local API (localhost:5050)
2. Search for macOS Chrome desktop fingerprints
3. Create profile with selected fingerprint
4. Configure proxy if provided
5. Start profile
6. Connect Playwright via CDP
7. Get existing browser context

#### `async _close_browser(self)`
1. Close Playwright browser connection
2. Stop Kameleo profile via API
3. Optionally delete profile (cleanup)

#### `async search(...)`
- Follow existing pattern from `IndeedPlaywrightScraper.search()`
- Implement pagination logic
- Add random delays between pages (5-10 seconds)
- Handle retry logic for browser crashes
- Return list of `JobListing` objects

#### `async _scrape_page(...)`
- Build Indeed search URL with parameters
- Navigate to page
- Extract job cards
- Parse job listings
- Extract company websites (reuse existing logic)
- Handle CAPTCHA detection
- Handle blocking detection

#### `_parse_job_card(self, card)`
- Reuse existing implementation from `IndeedPlaywrightScraper`
- Extract: title, company, location, description, URL, posted_date, salary
- Return JobListing object

#### `async _extract_company_website(...)`
- Reuse existing implementation from `IndeedPlaywrightScraper`
- Navigate to company page
- Extract website URL using multiple patterns

#### `_parse_posted_date(self, date_text)`
- Reuse existing implementation from `IndeedPlaywrightScraper`
- Parse relative dates ("2 days ago", "just posted", etc.)

### Configuration Schema

```python
config = {
    'proxy': 'http://username:password@host:port',  # Optional
    'kameleo_port': 5050,  # Optional, default 5050
    'headless': False,  # Kameleo profiles run in headed mode
    'timezone_id': 'America/Los_Angeles',  # Optional
    'locale': 'en-US',  # Optional
}
```

### Error Handling

#### Kameleo-Specific Errors
- **Kameleo not running**: Check if API endpoint is accessible, provide clear error message
- **No fingerprints found**: Handle case where no macOS Chrome fingerprints available
- **Profile creation failed**: Log error and fallback or raise exception
- **Connection timeout**: Retry logic with exponential backoff

#### Indeed-Specific Errors
- **CAPTCHA detected**: Log, save page HTML, return empty results
- **Rate limiting (429)**: Log, suggest wait time, return empty results
- **Blocking (403)**: Log, suggest using different proxy or wait time
- **No results found**: Log, check if page structure changed

### Logging Strategy

```python
logger.info("Initializing Kameleo client...")
logger.info(f"Using fingerprint: {fingerprint.id} (Chrome, macOS, Desktop)")
logger.info(f"Browser configured with proxy: {proxy_host}:{proxy_port}")
logger.info("Connected to Kameleo profile via Playwright CDP")
logger.info(f"Searching Indeed: query='{query}', location='{location}'")
logger.info(f"✅ Successfully parsed {len(jobs)} jobs from page {page_num}")
```

## Key Differences from IndeedPlaywrightScraper

### Removed Features
- Custom browser launch arguments (Kameleo handles this)
- Custom stealth scripts (Kameleo provides real fingerprints)
- Screen size randomization (Kameleo fingerprints include viewport)
- User agent randomization (Kameleo fingerprints include user agent)
- WebGL/hardware property spoofing (Kameleo handles this)

### Added Features
- Kameleo Local API client integration
- Browser fingerprint selection (macOS Chrome desktop)
- Profile lifecycle management (create, start, stop, cleanup)
- CDP connection instead of direct browser launch

### Maintained Features
- Proxy support (now via Kameleo profile)
- Random delays between pages
- CAPTCHA detection
- Company website extraction
- Job card parsing
- Error handling and retry logic

## Testing Strategy

### Manual Testing
1. **Basic Search**: Run search for 'technical product manager'
2. **Proxy Test**: Configure proxy and verify requests go through proxy
3. **Pagination**: Test multi-page scraping
4. **Company Website Extraction**: Verify company websites are extracted
5. **Error Handling**: Test with Kameleo stopped, invalid config, etc.

### Test Script Example
```python
import asyncio
from src.scrapers.indeed_kameleo import IndeedKameleoScraper

async def test_search():
    config = {
        'proxy': 'http://user:pass@proxy.example.com:8080',  # Optional
    }

    async with IndeedKameleoScraper(config) as scraper:
        jobs = await scraper.search(
            query='technical product manager',
            location='Remote',
            max_results=20
        )

        print(f"Found {len(jobs)} jobs")
        for job in jobs[:3]:
            print(f"- {job.title} at {job.company}")
            print(f"  URL: {job.url}")
            print(f"  Website: {job.company_website}")

asyncio.run(test_search())
```

## Prerequisites

### System Requirements
1. **Kameleo CLI**: Must be installed and running
   - Download from: https://www.kameleo.io/
   - Start Kameleo CLI before running scraper
   - Default port: 5050

2. **Python Packages**:
   ```bash
   pip install kameleo.local-api-client playwright
   playwright install chromium
   ```

3. **Environment Variables** (optional):
   ```bash
   export KAMELEO_PORT=5050
   export HTTPS_PROXY=http://user:pass@proxy.example.com:8080
   ```

## Implementation Phases

### Phase 1: Basic Structure (MVP)
- [ ] Create `IndeedKameleoScraper` class inheriting from `BaseScraper`
- [ ] Implement Kameleo client initialization
- [ ] Implement browser profile creation with macOS Chrome fingerprint
- [ ] Implement CDP connection to Kameleo profile
- [ ] Implement basic search functionality (reuse existing parsing logic)

### Phase 2: Proxy Support
- [ ] Add proxy configuration parsing
- [ ] Set proxy in Kameleo profile creation
- [ ] Test with proxy server

### Phase 3: Company Website Extraction
- [ ] Port `_extract_company_website()` method
- [ ] Test website extraction accuracy

### Phase 4: Error Handling & Robustness
- [ ] Add Kameleo-specific error handling
- [ ] Add retry logic for transient failures
- [ ] Add comprehensive logging
- [ ] Add cleanup on errors

### Phase 5: Testing & Documentation
- [ ] Create test script
- [ ] Test with various queries and locations
- [ ] Test pagination
- [ ] Document usage in README

## Usage Example

```python
import asyncio
from src.scrapers.indeed_kameleo import IndeedKameleoScraper

async def main():
    # Configure scraper
    config = {
        'proxy': 'http://user:pass@proxy.example.com:8080',  # Optional
        'kameleo_port': 5050,  # Default
    }

    # Use context manager for automatic cleanup
    async with IndeedKameleoScraper(config) as scraper:
        # Search for jobs
        jobs = await scraper.search(
            query='technical product manager',
            location='San Francisco, CA',
            max_results=50,
            remote_only=False
        )

        # Process results
        print(f"Found {len(jobs)} jobs:")
        for job in jobs:
            print(f"\n{job.title} at {job.company}")
            print(f"Location: {job.location}")
            print(f"URL: {job.url}")
            if job.company_website:
                print(f"Company Website: {job.company_website}")

if __name__ == '__main__':
    asyncio.run(main())
```

## Success Criteria

1. **Functional Requirements**
   - Successfully scrapes Indeed job listings
   - Supports proxy configuration
   - Uses Chrome browser with macOS fingerprint
   - Extracts company websites
   - Returns JobListing objects compatible with existing system

2. **Performance Requirements**
   - Scrapes 50 jobs in under 3 minutes (with delays)
   - Successfully bypasses Indeed's bot detection (low CAPTCHA rate)
   - Handles pagination correctly

3. **Quality Requirements**
   - Clean error handling with informative messages
   - Comprehensive logging for debugging
   - Proper resource cleanup (profiles, browsers)
   - Code follows existing patterns in codebase

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Kameleo CLI not running | High - scraper won't work | Check connection before starting, provide clear error message |
| Limited macOS fingerprints | Medium - fewer options | Fallback to any desktop Chrome fingerprint if macOS not available |
| Indeed still detects automation | High - blocking | Use residential proxies, add more random delays, implement CAPTCHA solver |
| Proxy connection fails | Medium - scraping fails | Validate proxy config, provide fallback to direct connection with warning |
| Profile cleanup failures | Low - resource leak | Implement comprehensive error handling in `__aexit__` |

## Future Enhancements

1. **Fingerprint Rotation**: Rotate between multiple fingerprints for different searches
2. **Session Management**: Reuse profiles across multiple searches
3. **CAPTCHA Solver Integration**: Automatically solve CAPTCHAs if detected
4. **Fingerprint Caching**: Cache available fingerprints to avoid repeated API calls
5. **Profile Pooling**: Maintain a pool of warm profiles for faster startup
6. **Metrics Collection**: Track success/failure rates, CAPTCHA encounters, etc.

## References

- Kameleo API Documentation: https://app.kameleo.io/api-reference
- Kameleo Python Examples: https://github.com/kameleo-io/local-api-examples/tree/master/python
- Indeed Playwright Scraper: `src/scrapers/indeed_playwright.py`
- Base Scraper: `src/scrapers/base.py`
