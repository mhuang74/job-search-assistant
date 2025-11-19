"""Indeed job board scraper"""
import asyncio
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

            # Randomize screen size to avoid fingerprinting
            screen = random.choice(SCREEN_SIZES)
            logger.info(f"Initializing browser ({browser_type}, headless={headless}, timezone={timezone_id}, screen={screen['width']}x{screen['height']})...")

            # Launch browser based on type
            if browser_type == 'firefox':
                # Firefox is often less detectable
                self.browser = await self.playwright.firefox.launch(
                    headless=headless,
                    args=[]  # Firefox doesn't need as many stealth args
                )
            else:
                # Chromium with stealth args
                self.browser = await self.playwright.chromium.launch(
                    headless=headless,
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

            # Check for explicit blocking messages
            if soup.find(string=re.compile(r'(blocked|unusual traffic|too many requests)', re.I)):
                logger.error("❌ Indeed detected unusual traffic - you may be blocked")
                logger.error("Your IP might be temporarily blocked. Wait 15-30 minutes.")
                return []

            # Find job cards
            job_cards = soup.find_all('div', class_=re.compile(r'job_seen_beacon'))

            if not job_cards:
                logger.warning(f"⚠️  No job cards found on page {page_num}")
                logger.debug("Possible reasons:")
                logger.debug("  - Indeed changed their HTML structure")
                logger.debug("  - Page didn't load completely")
                logger.debug("  - No results for your query")

                # Save page HTML for debugging
                debug_file = f"debug_indeed_page_{page_num}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.debug(f"💾 Saved page HTML to {debug_file} for inspection")

                return []

            jobs = []
            for card in job_cards:
                try:
                    job = self._parse_job_card(card)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Failed to parse job card: {e}")
                    logger.debug(f"Card HTML: {str(card)[:200]}")
                    continue

            logger.info(f"✅ Successfully parsed {len(jobs)} jobs from page {page_num}")
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

    def _parse_job_card(self, card) -> Optional[JobListing]:
        """Parse a single job card"""
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

            # Extract company
            company_elem = card.find('span', {'data-testid': 'company-name'})
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"

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

            return JobListing(
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
            )

        except Exception as e:
            logger.warning(f"Error parsing job card: {e}")
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
