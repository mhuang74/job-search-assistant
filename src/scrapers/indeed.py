"""Indeed job board scraper using SeleniumBase UC mode for anti-detection"""
import json
import os
import random
import re
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode, quote_plus
from loguru import logger
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..models import JobListing, JobBoard

# Pattern to extract mosaic data (embedded JSON with job listings)
MOSAIC_PATTERN = r'window\.mosaic\.providerData\["mosaic-provider-jobcards"\]\s*=\s*({.*?});'


class IndeedScraper(BaseScraper):
    """Indeed scraper using SeleniumBase UC mode for Cloudflare bypass"""

    def __init__(self, config: dict = None):
        super().__init__(JobBoard.INDEED, config)
        self.base_url = "https://www.indeed.com"
        self.sb = None
        self.request_count = 0
        self.max_requests_per_session = 3  # Rotate browser after this many requests

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self._close_browser()

    def _get_random_user_agent(self) -> str:
        """Get a random user agent string"""
        try:
            from fake_useragent import UserAgent
            ua = UserAgent()
            return ua.chrome
        except Exception:
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def _init_browser(self, headless: bool = True):
        """Initialize SeleniumBase with UC mode for anti-detection"""
        from seleniumbase import SB

        # Close existing browser if any
        self._close_browser()

        # Get proxy configuration
        proxy_url = self.config.get('proxy') or os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')

        # Parse proxy for SeleniumBase format
        proxy_arg = None
        if proxy_url:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(proxy_url)
                if parsed.username and parsed.password:
                    # Format: user:pass@host:port
                    proxy_arg = f"{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}"
                else:
                    proxy_arg = f"{parsed.hostname}:{parsed.port}"
                logger.info(f"Browser configured with proxy: {parsed.hostname}:{parsed.port}")
            except Exception as e:
                logger.warning(f"Failed to parse proxy URL: {e}")
                proxy_arg = None

        logger.info(f"Initializing SeleniumBase UC mode (headless={headless})...")

        # Create SB context with UC mode - returns context manager
        # We store the context manager and enter it
        sb_kwargs = {
            'uc': True,  # Undetected Chrome mode - critical for Cloudflare bypass
            'headless': headless,
            'test': False,  # Not running as test
        }

        if proxy_arg:
            sb_kwargs['proxy'] = proxy_arg

        # Store kwargs for creating new sessions
        self._sb_kwargs = sb_kwargs
        self.request_count = 0

        logger.info("SeleniumBase UC mode initialized")

    def _close_browser(self):
        """Close SeleniumBase browser"""
        if self.sb:
            try:
                self.sb.__exit__(None, None, None)
            except Exception:
                pass
            self.sb = None
        self.request_count = 0

    def _random_delay(self, min_sec: float, max_sec: float):
        """Add random delay to simulate human behavior"""
        delay = random.uniform(min_sec, max_sec)
        logger.debug(f"Waiting {delay:.1f}s...")
        time.sleep(delay)

    def _extract_jobs_from_mosaic(self, html: str) -> tuple[List[Dict[str, Any]], int]:
        """
        Extract job data from embedded mosaic JSON instead of DOM parsing.
        This is more reliable as the data structure is more stable than HTML selectors.

        Returns:
            Tuple of (jobs_list, total_count)
        """
        try:
            match = re.search(MOSAIC_PATTERN, html, re.DOTALL)
            if not match:
                logger.warning("Mosaic JSON data not found in page")
                return [], 0

            data = json.loads(match.group(1))

            # Extract job results
            jobs_data = data.get('metaData', {}).get('mosaicProviderJobCardsModel', {})
            jobs_list = jobs_data.get('results', [])

            # Get total count from tier summaries
            tier_summaries = jobs_data.get('tierSummaries', [])
            total_count = sum(tier.get('jobCount', 0) for tier in tier_summaries)

            logger.info(f"Extracted {len(jobs_list)} jobs from mosaic JSON (total available: {total_count})")
            return jobs_list, total_count

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse mosaic JSON: {e}")
            return [], 0
        except Exception as e:
            logger.error(f"Error extracting mosaic data: {e}")
            return [], 0

    def _parse_mosaic_job(self, job_data: Dict[str, Any]) -> Optional[JobListing]:
        """Parse a single job from mosaic JSON data"""
        try:
            job_key = job_data.get('jobkey', '')
            title = job_data.get('title', job_data.get('displayTitle', ''))
            company = job_data.get('company', 'Unknown')
            location = job_data.get('formattedLocation', job_data.get('jobLocationCity', 'Remote'))

            # Build job URL
            url = f"{self.base_url}/viewjob?jk={job_key}" if job_key else ""

            # Extract description snippet
            description = job_data.get('snippet', '')
            if not description:
                # Try to build from snippet items
                snippet_items = job_data.get('jobSnippetHtmlItems', [])
                description = ' '.join(snippet_items)

            # Parse date - Indeed provides relative dates like "3 days ago"
            date_str = job_data.get('formattedRelativeTime', '')
            posted_date = self._parse_posted_date(date_str)

            # Check if remote
            remote_location = job_data.get('remoteLocation', False)
            remote_type = "Remote" if remote_location or "remote" in location.lower() else None

            # Extract salary if available
            salary_info = job_data.get('extractedSalary', {})
            salary_min = None
            salary_max = None
            if salary_info:
                salary_min = salary_info.get('min')
                salary_max = salary_info.get('max')

            return JobListing(
                id=job_key or None,
                title=title,
                company=company,
                location=location,
                description=description,
                url=url,
                posted_date=posted_date,
                board_source=JobBoard.INDEED,
                remote_type=remote_type,
                scraped_at=datetime.now(),
                salary_min=salary_min,
                salary_max=salary_max,
            )

        except Exception as e:
            logger.warning(f"Error parsing mosaic job: {e}")
            return None

    async def search(
        self,
        query: str,
        location: str = "Remote",
        max_results: int = 50,
        remote_only: bool = True
    ) -> List[JobListing]:
        """
        Search for jobs on Indeed using SeleniumBase UC mode

        Args:
            query: Job search query (e.g., "software engineer")
            location: Location filter (default: "Remote")
            max_results: Maximum number of results to return
            remote_only: Filter for remote jobs only

        Returns:
            List of JobListing objects
        """
        logger.info(f"Searching Indeed: query='{query}', location='{location}', max_results={max_results}")

        # Allow headless mode override via config
        headless = self.config.get('headless', True)

        # Initialize browser settings
        self._init_browser(headless=headless)

        jobs = []
        page_num = 0
        max_pages = min((max_results // 10) + 1, 10)  # Indeed shows ~10 jobs per page

        from seleniumbase import SB

        try:
            while len(jobs) < max_results and page_num < max_pages:
                # Build search URL
                params = {
                    'q': query,
                    'l': location,
                    'start': page_num * 10,
                }

                if remote_only:
                    params['sc'] = '0kf:attr(DSQF7);'  # Remote filter

                url = f"{self.base_url}/jobs?{urlencode(params)}"
                logger.info(f"Scraping page {page_num}: {url}")

                # Create fresh browser context for better anti-detection
                # This helps avoid session-based tracking
                with SB(**self._sb_kwargs) as sb:
                    page_jobs = self._scrape_page_with_uc(sb, url, page_num)

                if not page_jobs:
                    logger.info(f"No more results on page {page_num}")
                    break

                jobs.extend(page_jobs)
                page_num += 1

                # Longer delay between pages (15-30s based on research)
                if page_num < max_pages and len(jobs) < max_results:
                    self._random_delay(15, 30)

        except Exception as e:
            logger.error(f"Search failed: {type(e).__name__}: {e}")
            logger.exception("Full traceback:")

        logger.info(f"Found {len(jobs)} jobs from Indeed")
        return jobs[:max_results]

    def _scrape_page_with_uc(self, sb, url: str, page_num: int) -> List[JobListing]:
        """
        Scrape a single page using SeleniumBase UC mode

        Uses uc_open_with_reconnect to disconnect chromedriver during page load,
        making it undetectable to Cloudflare during the critical verification moment.
        """
        try:
            # Add random delay before navigation (simulate human)
            self._random_delay(3, 7)

            # Use UC mode's special open method that disconnects during load
            # This is the key to bypassing Cloudflare detection
            logger.info("Opening page with UC reconnect mode...")
            sb.uc_open_with_reconnect(url, reconnect_time=5)

            # Wait for job cards to appear
            try:
                sb.wait_for_element_visible("[data-jk]", timeout=15)
                logger.info("Job cards detected on page")
            except Exception:
                logger.warning("Job card elements not found, checking for CAPTCHA or blocking...")

                # Check if we hit a CAPTCHA
                page_source = sb.get_page_source()
                if 'verify you' in page_source.lower() or 'captcha' in page_source.lower():
                    logger.error("CAPTCHA detected! Trying to solve...")

                    # Try UC mode's CAPTCHA handler (only works in non-headless)
                    if not self._sb_kwargs.get('headless', True):
                        try:
                            sb.uc_gui_click_captcha()
                            time.sleep(3)
                            # Refresh after CAPTCHA
                            sb.uc_open_with_reconnect(url, reconnect_time=5)
                        except Exception as ce:
                            logger.error(f"CAPTCHA solving failed: {ce}")
                            self._save_debug_html(page_source, f"captcha_page_{page_num}")
                            return []
                    else:
                        logger.error("CAPTCHA requires non-headless mode. Run with --no-headless")
                        self._save_debug_html(page_source, f"captcha_page_{page_num}")
                        return []

            # Get page source
            page_source = sb.get_page_source()

            # Try to extract from mosaic JSON first (more reliable)
            jobs_data, total_count = self._extract_jobs_from_mosaic(page_source)

            if jobs_data:
                jobs = []
                for job_data in jobs_data:
                    job = self._parse_mosaic_job(job_data)
                    if job:
                        jobs.append(job)

                logger.info(f"Successfully extracted {len(jobs)} jobs from mosaic JSON on page {page_num}")
                return jobs

            # Fallback to DOM parsing if mosaic not found
            logger.info("Mosaic JSON not found, falling back to DOM parsing...")
            return self._parse_jobs_from_dom(page_source, page_num)

        except Exception as e:
            logger.error(f"Failed to scrape page {page_num}: {type(e).__name__}: {e}")
            try:
                page_source = sb.get_page_source()
                self._save_debug_html(page_source, f"error_page_{page_num}")
            except:
                pass
            return []

    def _parse_jobs_from_dom(self, html: str, page_num: int) -> List[JobListing]:
        """Fallback: Parse jobs from DOM using BeautifulSoup"""
        soup = BeautifulSoup(html, 'html.parser')

        # Find job cards
        job_cards = soup.find_all('div', class_=re.compile(r'job_seen_beacon'))

        if not job_cards:
            logger.warning(f"No job cards found on page {page_num}")
            self._save_debug_html(html, f"no_jobs_page_{page_num}")
            return []

        jobs = []
        for card in job_cards:
            try:
                job = self._parse_job_card_dom(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.warning(f"Failed to parse job card: {e}")
                continue

        logger.info(f"Parsed {len(jobs)} jobs from DOM on page {page_num}")
        return jobs

    def _parse_job_card_dom(self, card) -> Optional[JobListing]:
        """Parse a single job card from DOM (fallback method)"""
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

    def _save_debug_html(self, html: str, name: str):
        """Save HTML for debugging"""
        filename = f"debug_indeed_{name}.html"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html)
            logger.info(f"Saved debug HTML to {filename}")
        except Exception as e:
            logger.warning(f"Failed to save debug HTML: {e}")

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
