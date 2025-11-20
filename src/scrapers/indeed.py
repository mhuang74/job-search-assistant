"""Indeed job board scraper"""
import asyncio
import os
import random
import re
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urlencode, quote_plus
from loguru import logger
from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..models import JobListing, JobBoard

# Screen size options for randomization (anti-fingerprinting)
SCREEN_SIZES = [
    {'width': 1024, 'height': 768},
    {'width': 1280, 'height': 800},
    {'width': 1366, 'height': 768},
    {'width': 1440, 'height': 900},
    {'width': 1920, 'height': 1080},
    {'width': 2560, 'height': 1440},
]


class IndeedScraper(BaseScraper):
    """Indeed scraper using Playwright for JavaScript rendering"""

    def __init__(self, config: dict = None):
        super().__init__(JobBoard.INDEED, config)
        self.base_url = "https://www.indeed.com"
        self.browser: Optional[Browser] = None
        self.playwright = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self._init_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_browser()

    async def _init_browser(self):
        """Initialize Playwright browser with anti-detection measures"""
        if self.browser is None:
            self.playwright = await async_playwright().start()

            # Allow headless mode override via config
            headless = self.config.get('headless', True)

            # Allow browser type override (firefox is often less detectable)
            browser_type = self.config.get('browser', 'chromium')  # 'chromium' or 'firefox'

            # Allow timezone/locale override via config (defaults to Taiwan)
            timezone_id = self.config.get('timezone_id', 'Asia/Taipei')
            locale = self.config.get('locale', 'en-US')  # Keep en-US since accessing Indeed.com

            # Get proxy configuration from config or environment
            proxy_url = self.config.get('proxy') or os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')

            # Parse proxy configuration for Playwright
            proxy_config = None
            if proxy_url:
                # Playwright expects proxy in format: {'server': 'http://host:port', 'username': '...', 'password': '...'}
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(proxy_url)
                    proxy_config = {'server': f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
                    if parsed.username:
                        proxy_config['username'] = parsed.username
                    if parsed.password:
                        proxy_config['password'] = parsed.password
                    logger.info(f"Browser configured with proxy: {parsed.scheme}://{parsed.hostname}:{parsed.port}")
                except Exception as e:
                    logger.warning(f"Failed to parse proxy URL '{proxy_url}': {e}")
                    proxy_config = None

            # Randomize screen size to avoid fingerprinting
            screen = random.choice(SCREEN_SIZES)
            logger.info(f"Initializing browser ({browser_type}, headless={headless}, timezone={timezone_id}, screen={screen['width']}x{screen['height']})...")

            # Prepare browser launch kwargs
            launch_kwargs = {
                'headless': headless,
            }
            if proxy_config:
                launch_kwargs['proxy'] = proxy_config

            # Launch browser based on type
            if browser_type == 'firefox':
                # Firefox is often less detectable
                self.browser = await self.playwright.firefox.launch(
                    **launch_kwargs,
                    args=[]  # Firefox doesn't need as many stealth args
                )
            else:
                # Chromium with stealth args
                self.browser = await self.playwright.chromium.launch(
                    **launch_kwargs,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        f'--window-size={screen["width"]},{screen["height"]}',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--disable-site-isolation-trials',
                        '--disable-features=VizDisplayCompositor',
                    ]
                )

            # Create a context with anti-detection
            # Use Taiwan timezone by default to match user's actual location
            self.context = await self.browser.new_context(
                viewport=screen,
                user_agent=self._get_random_user_agent(),
                locale=locale,
                timezone_id=timezone_id,
            )

            # Add extra headers to look more like a real browser
            await self.context.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
            })

            logger.info("✅ Browser initialized with anti-detection measures")

    async def _close_browser(self):
        """Close Playwright browser"""
        if hasattr(self, 'context') and self.context:
            await self.context.close()
            self.context = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
            logger.info("Browser closed")

    async def search(
        self,
        query: str,
        location: str = "Remote",
        max_results: int = 50,
        remote_only: bool = True
    ) -> List[JobListing]:
        """
        Search for jobs on Indeed

        Args:
            query: Job search query (e.g., "software engineer")
            location: Location filter (default: "Remote")
            max_results: Maximum number of results to return
            remote_only: Filter for remote jobs only

        Returns:
            List of JobListing objects
        """
        logger.info(f"Searching Indeed: query='{query}', location='{location}', max_results={max_results}")

        if self.browser is None:
            await self._init_browser()

        jobs = []
        page_num = 0
        max_pages = min((max_results // 15) + 1, 10)  # Indeed shows ~15 jobs per page

        while len(jobs) < max_results and page_num < max_pages:
            # Retry logic for browser crashes
            max_retries = 3
            retry_count = 0
            page_jobs = []

            while retry_count < max_retries:
                try:
                    page_jobs = await self._scrape_page(query, location, page_num, remote_only)
                    break  # Success, exit retry loop
                except Exception as e:
                    error_name = type(e).__name__
                    error_str = str(e)

                    # Check if it's a browser/connection closed error
                    is_browser_closed = any([
                        'TargetClosedError' in error_name,
                        'BrowserClosedError' in error_name,
                        'Connection closed' in error_str,
                        'Target page, context or browser has been closed' in error_str,
                        'Session closed' in error_str,
                    ])

                    if is_browser_closed:
                        retry_count += 1
                        if retry_count < max_retries:
                            wait_time = 2 ** retry_count  # Exponential backoff: 2, 4, 8 seconds
                            logger.warning(f"Browser closed unexpectedly ({error_name}). Retrying in {wait_time}s... (attempt {retry_count}/{max_retries})")
                            await asyncio.sleep(wait_time)
                            # Reinitialize browser
                            await self._close_browser()
                            await self._init_browser()
                        else:
                            logger.error(f"Failed after {max_retries} retries. Indeed is aggressively blocking automation.")
                            logger.error(f"Error: {error_str}")
                            logger.error("")
                            logger.error("⚠️  Indeed is detecting Playwright/Chromium as a bot")
                            logger.error("")
                            logger.error("Next steps to try:")
                            logger.error("  1. Run with --no-headless to see what Indeed shows:")
                            logger.error("     python main.py search 'your query' --no-headless --verbose")
                            logger.error("")
                            logger.error("  2. Try using Firefox instead (config option)")
                            logger.error("")
                            logger.error("  3. Wait 15-30 minutes, then try again")
                            logger.error("")
                            logger.error("  4. Use a proxy or VPN to change your IP")
                            raise
                    else:
                        # Different error, don't retry
                        raise

            if not page_jobs:
                logger.info(f"No more results on page {page_num}")
                break

            jobs.extend(page_jobs)
            page_num += 1

            # Random delay between pages (increased to 5-10s based on research)
            await self._random_delay(5, 10)

        logger.info(f"Found {len(jobs)} jobs from Indeed")
        return jobs[:max_results]

    async def _scrape_page(
        self,
        query: str,
        location: str,
        page_num: int,
        remote_only: bool
    ) -> List[JobListing]:
        """Scrape a single page of Indeed results"""
        # Build search URL
        params = {
            'q': query,
            'l': location,
            'start': page_num * 10,
        }

        if remote_only:
            params['sc'] = '0kf:attr(DSQF7);'  # Remote filter

        url = f"{self.base_url}/jobs?{urlencode(params)}"
        logger.debug(f"Scraping: {url}")

        page = None
        try:
            # Use context instead of browser directly for better anti-detection
            if hasattr(self, 'context'):
                page = await self.context.new_page()
            else:
                page = await self.browser.new_page()

            page.set_default_timeout(30000)

            # Comprehensive stealth scripts to mask automation (based on selenium-stealth)
            # Randomize hardware properties
            hardware_concurrency = random.choice([2, 4, 8, 16])
            device_memory = random.choice([4, 8, 16])

            await page.add_init_script(f"""
                // Mask webdriver property
                Object.defineProperty(navigator, 'webdriver', {{
                    get: () => undefined
                }});

                // Override chrome property
                window.chrome = {{
                    runtime: {{}}
                }};

                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({{ state: Notification.permission }}) :
                        originalQuery(parameters)
                );

                // Override plugins to look like real browser
                Object.defineProperty(navigator, 'plugins', {{
                    get: () => [1, 2, 3, 4, 5]
                }});

                // Override languages to match locale
                Object.defineProperty(navigator, 'languages', {{
                    get: () => ['en-US', 'en']
                }});

                // WebGL vendor spoofing (critical for anti-fingerprinting)
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                    if (parameter === 37445) {{
                        return 'Intel Inc.';  // UNMASKED_VENDOR_WEBGL
                    }}
                    if (parameter === 37446) {{
                        return 'Intel Iris OpenGL Engine';  // UNMASKED_RENDERER_WEBGL
                    }}
                    return getParameter.call(this, parameter);
                }};

                // Navigator vendor
                Object.defineProperty(navigator, 'vendor', {{
                    get: () => 'Google Inc.'
                }});

                // Hardware properties (randomized)
                Object.defineProperty(navigator, 'hardwareConcurrency', {{
                    get: () => {hardware_concurrency}
                }});

                Object.defineProperty(navigator, 'deviceMemory', {{
                    get: () => {device_memory}
                }});

                // Platform
                Object.defineProperty(navigator, 'platform', {{
                    get: () => 'Win32'
                }});

                // Max touch points
                Object.defineProperty(navigator, 'maxTouchPoints', {{
                    get: () => 0
                }});
            """)

            # Add random delay before navigation (simulate human behavior)
            delay = random.uniform(3.0, 7.0)  # Increased from 1.5-3.5s based on research
            logger.debug(f"Adding {delay:.2f}s delay to simulate human behavior...")
            await page.wait_for_timeout(int(delay * 1000))

            # Navigate to search results
            logger.info(f"Navigating to Indeed page {page_num}...")
            try:
                response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            except Exception as nav_error:
                logger.error(f"Navigation failed: {type(nav_error).__name__}: {nav_error}")
                logger.error("This often means Indeed detected automation and closed the browser")
                logger.error("Try running with --no-headless flag to debug")
                raise

            # Log response details
            logger.info(f"Response status: {response.status}")
            logger.debug(f"Response URL: {response.url}")
            logger.debug(f"Response headers: {response.headers}")

            # Check for blocking
            if response.status == 403:
                logger.error("❌ Indeed returned 403 Forbidden - likely blocked")
                logger.error("Try using a different user agent or enable headless=False")
                page_content = await page.content()
                logger.debug(f"Page content preview: {page_content[:500]}")
                return []
            elif response.status == 429:
                logger.error("❌ Indeed returned 429 Too Many Requests - rate limited")
                logger.error("Wait a few minutes before trying again")
                return []
            elif response.status >= 400:
                logger.error(f"❌ Indeed returned error status: {response.status}")
                page_content = await page.content()
                logger.debug(f"Page content preview: {page_content[:500]}")
                return []

            # Wait for JavaScript
            await page.wait_for_timeout(2000)

            # Get page content
            content = await page.content()

            # Parse with BeautifulSoup first
            soup = BeautifulSoup(content, 'html.parser')

            # Check for actual CAPTCHA elements (more specific than just searching for the word)
            captcha_elements = soup.find_all(['div', 'iframe', 'form'],
                                            class_=re.compile(r'(recaptcha|captcha-container|hcaptcha)', re.I))
            has_captcha_challenge = soup.find(string=re.compile(r'(verify you.re human|solve.*captcha|complete.*verification)', re.I))

            if captcha_elements or has_captcha_challenge:
                logger.error("❌ CAPTCHA detected on Indeed page!")
                logger.error("Indeed is showing a verification challenge.")
                # Save HTML for inspection
                debug_file = f"debug_indeed_captcha_{page_num}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.error(f"💾 Saved page HTML to {debug_file} for inspection")
                return []

            # Find job cards FIRST (to avoid false positive blocking detection)
            job_cards = soup.find_all('div', class_=re.compile(r'job_seen_beacon'))

            if not job_cards:
                logger.warning(f"⚠️  No job cards found on page {page_num}")

                # Save page HTML for debugging
                debug_file = f"debug_indeed_page_{page_num}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.warning(f"💾 Saved page HTML to {debug_file} for inspection")

                # Check if this is due to blocking (only if no job cards found)
                # Look for actual blocking UI elements, not just keywords
                blocking_indicators = [
                    soup.find('div', class_=re.compile(r'(blocked|access.*denied)', re.I)),
                    soup.find(id=re.compile(r'(blocked|access.*denied)', re.I)),
                    soup.find('h1', string=re.compile(r'(blocked|access.*denied|unusual traffic)', re.I)),
                ]

                if any(blocking_indicators):
                    logger.error("❌ Indeed may be blocking your requests")
                    logger.error("Detected blocking UI elements on page")
                    logger.error(f"Check {debug_file} to see what Indeed is showing")
                else:
                    logger.debug("Possible reasons for no job cards:")
                    logger.debug("  - Indeed changed their HTML structure")
                    logger.debug("  - No results for your query")
                    logger.debug("  - JavaScript not fully loaded")
                    logger.debug(f"  - Check {debug_file} to see what's on the page")

                return []

            # Parse job cards
            job_data_list = []
            for card in job_cards:
                try:
                    job_data = self._parse_job_card(card)
                    if job_data:
                        job_data_list.append(job_data)
                except Exception as e:
                    logger.warning(f"Failed to parse job card: {e}")
                    logger.debug(f"Card HTML: {str(card)[:200]}")
                    continue

            logger.info(f"✅ Successfully parsed {len(job_data_list)} jobs from page {page_num}")

            # Extract company websites for jobs with company URLs
            # Use a set to track companies we've already fetched to avoid duplicates
            fetched_companies = {}
            jobs = []

            logger.info(f"🔗 Extracting company websites for {len(job_data_list)} job(s)...")

            for idx, job_data in enumerate(job_data_list, 1):
                job_listing = job_data['job_listing']
                company_url = job_data['company_url']

                logger.info(f"\n{'='*60}")
                logger.info(f"Job {idx}/{len(job_data_list)}: {job_listing.title} at {job_listing.company}")
                logger.info(f"{'='*60}")

                # Try to fetch company website if we have a company URL
                if company_url:
                    logger.info(f"📍 Company URL found: {company_url}")

                    # Check if we already fetched this company
                    if company_url in fetched_companies:
                        company_website = fetched_companies[company_url]
                        logger.info(f"💾 Using cached company website for {job_listing.company}: {company_website or 'None'}")
                    else:
                        # Fetch company website
                        logger.info(f"🚀 Fetching company website for: {job_listing.company}")
                        company_website = await self._extract_company_website(page, company_url)
                        fetched_companies[company_url] = company_website

                        # Add small delay between company page fetches to avoid detection
                        await self._random_delay(1, 2)

                    # Update job listing with company website
                    if company_website:
                        job_listing.company_website = company_website
                        logger.info(f"✅ Website set for {job_listing.company}: {company_website}")
                    else:
                        logger.info(f"⚠️  No website found for {job_listing.company}")
                else:
                    logger.info(f"⚠️  No company URL found in job card for {job_listing.company}")

                jobs.append(job_listing)

            return jobs

        except Exception as e:
            logger.error(f"❌ Failed to scrape page {page_num}: {type(e).__name__}: {e}")
            logger.exception("Full exception traceback:")

            if page:
                try:
                    # Take screenshot for debugging
                    screenshot_path = f"debug_indeed_error_page_{page_num}.png"
                    await page.screenshot(path=screenshot_path)
                    logger.error(f"📸 Saved error screenshot to {screenshot_path}")
                except:
                    pass

            return []
        finally:
            if page:
                await page.close()

    def _parse_job_card(self, card) -> Optional[dict]:
        """Parse a single job card and return dict with job data and company URL"""
        try:
            # Extract title and URL
            title_elem = card.find('h2', class_='jobTitle')
            if not title_elem:
                return None

            title_link = title_elem.find('a')
            if not title_link:
                return None

            title = title_link.get_text(strip=True)
            job_key = title_link.get('data-jk') or title_link.get('id', '').replace('job_', '')
            url = f"{self.base_url}/viewjob?jk={job_key}" if job_key else ""

            # Extract company and company URL
            company_elem = card.find('span', {'data-testid': 'company-name'})
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"

            # Try to find company link - it might be in the parent or a sibling element
            company_url = None
            if company_elem:
                # Look for a link in the parent hierarchy
                company_link = company_elem.find_parent('a')
                if not company_link:
                    # Sometimes the link is a sibling or nearby element
                    company_container = company_elem.find_parent('div')
                    if company_container:
                        company_link = company_container.find('a', href=re.compile(r'/cmp/'))

                if company_link and company_link.get('href'):
                    href = company_link.get('href')
                    # Ensure it's a full URL
                    if href.startswith('/'):
                        company_url = f"{self.base_url}{href}"
                    else:
                        company_url = href

            # Extract location
            location_elem = card.find('div', {'data-testid': 'text-location'})
            location = location_elem.get_text(strip=True) if location_elem else "Remote"

            # Extract description snippet
            desc_elem = card.find('div', class_='job-snippet')
            description = desc_elem.get_text(strip=True) if desc_elem else ""

            # Extract posted date
            date_elem = card.find('span', class_='date')
            posted_date = self._parse_posted_date(date_elem.get_text(strip=True) if date_elem else "")

            # Extract salary if available
            salary_elem = card.find('div', class_=re.compile(r'salary-snippet'))
            salary_text = salary_elem.get_text(strip=True) if salary_elem else None

            return {
                'job_listing': JobListing(
                    id=job_key or None,
                    title=title,
                    company=company,
                    location=location,
                    description=description,
                    url=url,
                    posted_date=posted_date,
                    board_source=JobBoard.INDEED,
                    remote_type="Remote" if "remote" in location.lower() else None,
                    scraped_at=datetime.now()
                ),
                'company_url': company_url
            }

        except Exception as e:
            logger.warning(f"Error parsing job card: {e}")
            return None

    async def _extract_company_website(self, page: Page, company_url: str) -> Optional[str]:
        """
        Navigate to company page and extract website URL

        Args:
            page: Playwright page object
            company_url: URL to company page on Indeed

        Returns:
            Company website URL if found, None otherwise
        """
        if not company_url:
            return None

        try:
            logger.info(f"🌐 Opening company page: {company_url}")

            # Navigate to company page
            response = await page.goto(company_url, wait_until='domcontentloaded', timeout=15000)
            logger.info(f"   📄 Response status: {response.status}")

            if response.status >= 400:
                logger.warning(f"   ❌ Failed to load company page (status {response.status})")
                return None

            # Wait for page to load
            await page.wait_for_timeout(1000)

            # Get page content
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Look for the "Link" box on the About Company page
            # Indeed typically shows company website in a div with specific patterns
            # Try multiple selectors to find the website link

            # Pattern 1: Look for a "Website" or "Link" label
            website_candidates = []
            logger.info(f"   🔍 Searching for company website using Pattern 1 (Website/Link labels)...")

            # Find all links that might be the company website
            pattern1_matches = 0
            for link_elem in soup.find_all('a', href=True):
                href = link_elem.get('href', '')
                text = link_elem.get_text(strip=True).lower()

                # Check if this is labeled as website/link
                parent_text = ''
                if link_elem.parent:
                    parent_text = link_elem.parent.get_text(strip=True).lower()

                # Look for indicators this is the company website
                is_website = any([
                    'website' in text or 'website' in parent_text,
                    'link' in parent_text and len(text) > 5,  # "Link" label with actual URL text
                    text == 'visit website',
                    text == 'company website',
                ])

                # Exclude Indeed internal links
                is_external = not any([
                    'indeed.com' in href,
                    href.startswith('/'),
                    href.startswith('#'),
                    'mailto:' in href,
                    'tel:' in href,
                ])

                if is_website and is_external:
                    website_candidates.append(href)
                    pattern1_matches += 1
                    logger.info(f"   ✓ Pattern 1 match: '{text[:50]}' -> {href}")

            logger.info(f"   📊 Pattern 1 found {pattern1_matches} candidate(s)")

            # Pattern 2: Look in structured data containers
            # Indeed may have a "Company Details" or "About" section
            logger.info(f"   🔍 Searching for company website using Pattern 2 (Company info sections)...")
            info_sections = soup.find_all(['div', 'section'], class_=re.compile(r'(company.*info|about|details)', re.I))
            logger.info(f"   📊 Found {len(info_sections)} company info section(s)")

            pattern2_matches = 0
            for section in info_sections:
                links = section.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    if href and not any([
                        'indeed.com' in href,
                        href.startswith('/'),
                        href.startswith('#'),
                        'mailto:' in href,
                        'tel:' in href,
                    ]):
                        # Check if nearby text suggests this is a website
                        nearby_text = link.get_text(strip=True).lower()
                        if nearby_text and len(nearby_text) > 3:
                            website_candidates.append(href)
                            pattern2_matches += 1
                            logger.info(f"   ✓ Pattern 2 match: '{nearby_text[:50]}' -> {href}")

            logger.info(f"   📊 Pattern 2 found {pattern2_matches} candidate(s)")

            # Pattern 3: Look for data attributes or specific CSS classes
            logger.info(f"   🔍 Searching for company website using Pattern 3 (Data attributes)...")
            website_links = soup.find_all('a', {'data-testid': re.compile(r'(website|link|url)', re.I)})
            pattern3_matches = 0
            for link in website_links:
                href = link.get('href', '')
                if href and 'indeed.com' not in href and not href.startswith('/'):
                    website_candidates.append(href)
                    pattern3_matches += 1
                    logger.info(f"   ✓ Pattern 3 match: data-testid -> {href}")

            logger.info(f"   📊 Pattern 3 found {pattern3_matches} candidate(s)")

            if website_candidates:
                # Return the first valid candidate
                website_url = website_candidates[0]
                logger.info(f"   ✅ EXTRACTED WEBSITE: {website_url}")
                logger.info(f"   📊 Total candidates found: {len(website_candidates)}")
                if len(website_candidates) > 1:
                    logger.info(f"   ℹ️  Other candidates: {', '.join(website_candidates[1:3])}")
                return website_url

            logger.info("   ❌ No company website found on page")
            return None

        except Exception as e:
            logger.warning(f"   ❌ Error extracting company website: {type(e).__name__}: {e}")
            return None

    def _parse_posted_date(self, date_text: str) -> datetime:
        """Parse Indeed's relative date format (e.g., '2 days ago')"""
        date_text = date_text.lower().strip()

        if not date_text or date_text == "just posted" or date_text == "today":
            return datetime.now()

        # Extract number from text
        match = re.search(r'(\d+)', date_text)
        if not match:
            return datetime.now()

        number = int(match.group(1))

        if 'hour' in date_text:
            return datetime.now() - timedelta(hours=number)
        elif 'day' in date_text:
            return datetime.now() - timedelta(days=number)
        elif 'week' in date_text:
            return datetime.now() - timedelta(weeks=number)
        elif 'month' in date_text:
            return datetime.now() - timedelta(days=number * 30)
        else:
            return datetime.now()

    async def get_job_details(self, job_url: str) -> Optional[JobListing]:
        """Get detailed job information (not implemented for MVP)"""
        # For MVP, we use the job card data
        # This can be enhanced to fetch full job descriptions
        logger.debug(f"Job details fetching not implemented for MVP: {job_url}")
        return None
