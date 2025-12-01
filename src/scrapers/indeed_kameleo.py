"""Indeed job board scraper using Playwright with Kameleo browser profiles"""
import asyncio
import os
import random
import re
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urlencode
from loguru import logger
from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup

# Kameleo imports
from kameleo.local_api_client import KameleoLocalApiClient
from kameleo.local_api_client.models import (
    CreateProfileRequest,
    ProxyConnectionType,
    Server,
)

from .base import BaseScraper
from ..models import JobListing, JobBoard


class IndeedKameleoScraper(BaseScraper):
    """Indeed scraper using Playwright with Kameleo browser profiles for enhanced anti-detection"""

    def __init__(self, config: dict = None):
        super().__init__(JobBoard.INDEED, config)
        self.base_url = "https://www.indeed.com"
        self.browser: Optional[Browser] = None
        self.playwright = None
        self.kameleo_client: Optional[KameleoLocalApiClient] = None
        self.kameleo_profile = None
        self.kameleo_port = int(os.getenv('KAMELEO_PORT', '5050'))

        # Override kameleo_port from config if provided
        if config:
            self.kameleo_port = config.get('kameleo_port', self.kameleo_port)

    async def __aenter__(self):
        """Async context manager entry"""
        await self._init_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_browser()

    async def _init_browser(self):
        """Initialize Playwright browser with Kameleo profile"""
        if self.browser is not None:
            return

        try:
            # Step 1: Connect to Kameleo Local API
            logger.info("Initializing Kameleo client...")
            kameleo_base_url = f"http://localhost:{self.kameleo_port}"

            try:
                self.kameleo_client = KameleoLocalApiClient(endpoint=kameleo_base_url)
                logger.info(f"✅ Connected to Kameleo API at {kameleo_base_url}")
            except Exception as e:
                logger.error(f"❌ Failed to connect to Kameleo Local API at {kameleo_base_url}")
                logger.error(f"Error: {e}")
                logger.error("")
                logger.error("Please ensure:")
                logger.error("  1. Kameleo CLI is installed and running")
                logger.error("  2. Kameleo is running on port 5050 (or set KAMELEO_PORT env var)")
                logger.error("  3. Download from: https://www.kameleo.io/")
                raise

            # Step 2: Search for macOS Safari desktop fingerprints
            logger.info("Searching for macOS Safari desktop fingerprints...")
            try:
                fingerprints = await asyncio.to_thread(
                    self.kameleo_client.fingerprint.search_fingerprints,
                    device_type='desktop',
                    browser_product='safari',
                    os_family='macos'
                )

                if not fingerprints:
                    # Fallback: Try any desktop Chrome fingerprint
                    logger.warning("No macOS fingerprints found, trying any desktop Chrome fingerprint...")
                    fingerprints = await asyncio.to_thread(
                        self.kameleo_client.fingerprint.search_fingerprints,
                        device_type='desktop',
                        browser_product='chrome'
                    )

                if not fingerprints:
                    raise Exception("No suitable fingerprints found in Kameleo")

                fingerprint = fingerprints[0]
                # Build descriptive name from fingerprint attributes
                fp_description = f"{fingerprint.device.type} - {fingerprint.browser.product} {fingerprint.browser.version} on {fingerprint.os.family}"
                logger.info(f"Using fingerprint: {fp_description}")
                logger.debug(f"Fingerprint ID: {fingerprint.id}")

            except Exception as e:
                logger.error(f"❌ Failed to search fingerprints: {e}")
                raise

            # Step 3: Prepare proxy configuration if provided
            proxy_choice = None
            proxy_url = self.config.get('proxy') or os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')

            if proxy_url:
                try:
                    from urllib.parse import urlparse
                    from kameleo.local_api_client.models import ProxyChoice
                    parsed = urlparse(proxy_url)

                    # Determine proxy type from scheme
                    proxy_type = ProxyConnectionType.HTTP
                    if parsed.scheme in ['socks5', 'socks5h']:
                        proxy_type = ProxyConnectionType.SOCKS5
                    elif parsed.scheme in ['ssh']:
                        proxy_type = ProxyConnectionType.SSH
                    
                    # Ensure port is present
                    port = parsed.port
                    if not port:
                        if parsed.scheme == 'http':
                            port = 80
                        elif parsed.scheme == 'https':
                            port = 443
                        elif parsed.scheme == 'socks5':
                            port = 1080
                        else:
                            logger.warning(f"No port specified in proxy URL '{proxy_url}', defaulting to 80")
                            port = 80

                    # Create Kameleo Server object for proxy
                    server = Server(
                        host=parsed.hostname,
                        port=port,
                        id=parsed.username if parsed.username else None,
                        secret=parsed.password if parsed.password else None,
                    )

                    # Create ProxyChoice
                    proxy_choice = ProxyChoice(
                        value=proxy_type,
                        extra=server
                    )
                    
                    auth_status = "with auth" if parsed.username else "no auth"
                    logger.info(f"Browser configured with proxy: {parsed.scheme}://{parsed.hostname}:{port} ({auth_status})")
                    if parsed.username:
                        # Log masked password for debugging
                        masked_pass = '*' * len(parsed.password) if parsed.password else ''
                        logger.debug(f"Proxy Auth - User: {parsed.username}, Pass: {masked_pass}")

                except Exception as e:
                    logger.warning(f"Failed to parse proxy URL '{proxy_url}': {e}")
                    proxy_choice = None

            # Step 4: Create Kameleo profile
            logger.info("Creating Kameleo profile...")
            profile_name = f"Indeed Scraper - {datetime.now().strftime('%Y%m%d_%H%M%S')}"

            create_profile_request = CreateProfileRequest(
                fingerprint_id=fingerprint.id,
                name=profile_name,
            )

            # Add proxy if configured
            if proxy_choice:
                create_profile_request.proxy = proxy_choice

            try:
                self.kameleo_profile = await asyncio.to_thread(
                    self.kameleo_client.profile.create_profile,
                    create_profile_request
                )
                logger.info(f"✅ Created Kameleo profile: {profile_name} (ID: {self.kameleo_profile.id})")
            except Exception as e:
                logger.error(f"❌ Failed to create Kameleo profile: {e}")
                raise

            # Step 5: Start the Kameleo profile
            logger.info("Starting Kameleo profile...")
            try:
                await asyncio.to_thread(
                    self.kameleo_client.profile.start_profile,
                    self.kameleo_profile.id
                )
                logger.info("✅ Kameleo profile started")
            except Exception as e:
                logger.error(f"❌ Failed to start Kameleo profile: {e}")
                # Cleanup: delete profile if start failed
                try:
                    await asyncio.to_thread(
                        self.kameleo_client.profile.delete_profile,
                        self.kameleo_profile.id
                    )
                except:
                    pass
                raise

            # Step 6: Connect Playwright via CDP
            logger.info("Connecting Playwright to Kameleo profile via CDP...")
            try:
                self.playwright = await async_playwright().start()

                # Build WebSocket endpoint for CDP connection
                ws_endpoint = f"ws://localhost:{self.kameleo_port}/playwright/{self.kameleo_profile.id}"
                logger.debug(f"CDP endpoint: {ws_endpoint}")

                # Connect to existing browser via CDP
                self.browser = await self.playwright.chromium.connect_over_cdp(ws_endpoint)
                logger.info("✅ Connected to Kameleo profile via Playwright CDP")

                # Get the existing browser context (don't create a new one)
                contexts = self.browser.contexts
                if contexts:
                    self.context = contexts[0]
                    logger.info("✅ Using existing Kameleo browser context")
                else:
                    logger.warning("No existing context found, creating new one")
                    self.context = await self.browser.new_context()

            except Exception as e:
                logger.error(f"❌ Failed to connect Playwright to Kameleo: {e}")
                # Cleanup
                try:
                    await asyncio.to_thread(
                        self.kameleo_client.profile.stop_profile,
                        self.kameleo_profile.id
                    )
                    await asyncio.to_thread(
                        self.kameleo_client.profile.delete_profile,
                        self.kameleo_profile.id
                    )
                except:
                    pass
                raise

            logger.info("✅ Browser initialized with Kameleo anti-detection")

        except Exception as e:
            logger.error(f"❌ Browser initialization failed: {e}")
            raise

    async def _close_browser(self):
        """Close Playwright browser and cleanup Kameleo profile"""
        # Close Playwright connection
        if hasattr(self, 'context') and self.context:
            try:
                await self.context.close()
            except:
                pass
            self.context = None

        if self.browser:
            try:
                await self.browser.close()
            except:
                pass
            self.browser = None

        if self.playwright:
            try:
                await self.playwright.stop()
            except:
                pass
            self.playwright = None

        # Stop and delete Kameleo profile
        if self.kameleo_client and self.kameleo_profile:
            try:
                logger.info("Stopping Kameleo profile...")
                await asyncio.to_thread(
                    self.kameleo_client.profile.stop_profile,
                    self.kameleo_profile.id
                )
                logger.info("✅ Kameleo profile stopped")
            except Exception as e:
                logger.warning(f"Failed to stop Kameleo profile: {e}")

            try:
                logger.info("Deleting Kameleo profile...")
                await asyncio.to_thread(
                    self.kameleo_client.profile.delete_profile,
                    self.kameleo_profile.id
                )
                logger.info("✅ Kameleo profile deleted")
            except Exception as e:
                logger.warning(f"Failed to delete Kameleo profile: {e}")

            self.kameleo_profile = None

        logger.info("Browser closed and Kameleo profile cleaned up")

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
            query: Job search query (e.g., "technical product manager")
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
                    logger.error(f"❌ Error scraping page {page_num + 1}: {e}")
                    
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
                            raise
                    else:
                        # Different error, don't retry
                        raise

            if not page_jobs:
                logger.info(f"No more results on page {page_num}")
                break

            jobs.extend(page_jobs)
            page_num += 1

            # Random delay between pages (5-10 seconds)
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
            # Create new page from context
            page = await self.context.new_page()
            page.set_default_timeout(30000)

            # Add random delay before navigation (simulate human behavior)
            delay = random.uniform(3.0, 7.0)
            logger.debug(f"Adding {delay:.2f}s delay to simulate human behavior...")
            await page.wait_for_timeout(int(delay * 1000))

            # Navigate to search results
            logger.info(f"Navigating to Indeed page {page_num}...")
            try:
                response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            except Exception as nav_error:
                logger.error(f"Navigation failed: {type(nav_error).__name__}: {nav_error}")
                logger.error("This often means Indeed detected automation and closed the browser")
                raise

            # Log response details
            logger.info(f"Response status: {response.status}")
            logger.debug(f"Response URL: {response.url}")

            # Check for blocking
            if response.status == 403:
                logger.error("❌ Indeed returned 403 Forbidden - likely blocked")
                return []
            elif response.status == 429:
                logger.error("❌ Indeed returned 429 Too Many Requests - rate limited")
                logger.error("Wait a few minutes before trying again")
                return []
            elif response.status >= 400:
                logger.error(f"❌ Indeed returned error status: {response.status}")
                return []

            # Wait for JavaScript
            await page.wait_for_timeout(2000)

            # Get page content
            content = await page.content()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')

            # Check for CAPTCHA
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

            # Find job cards
            job_cards = soup.find_all('div', class_=re.compile(r'job_seen_beacon'))

            if not job_cards:
                logger.warning(f"⚠️  No job cards found on page {page_num}")

                # Save page HTML for debugging
                debug_file = f"debug_indeed_page_{page_num}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.warning(f"💾 Saved page HTML to {debug_file} for inspection")

                # Check if this is due to blocking
                blocking_indicators = [
                    soup.find('div', class_=re.compile(r'(blocked|access.*denied)', re.I)),
                    soup.find('h1', string=re.compile(r'(blocked|access.*denied|unusual traffic)', re.I)),
                ]

                if any(blocking_indicators):
                    logger.error("❌ Indeed may be blocking your requests")
                    logger.error(f"Check {debug_file} to see what Indeed is showing")

                return []

            # Parse job cards
            jobs = []
            for card in job_cards:
                try:
                    job = self._parse_job_card(card)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Failed to parse job card: {e}")
                    continue

            logger.info(f"✅ Successfully parsed {len(jobs)} jobs from page {page_num}")
            
            # Log found jobs
            for idx, job in enumerate(jobs, 1):
                logger.info(f"Job {idx}/{len(jobs)}: {job.title} at {job.company}")

            return jobs

        except Exception as e:
            logger.error(f"❌ Failed to scrape page {page_num}: {type(e).__name__}: {e}")
            logger.exception("Full exception traceback:")

            if page:
                try:
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
        """Parse a single job card and return JobListing"""
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
        logger.debug(f"Job details fetching not implemented for MVP: {job_url}")
        return None
