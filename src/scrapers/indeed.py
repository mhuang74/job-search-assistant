"""Indeed job board scraper"""
import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urlencode, quote_plus
from loguru import logger
from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..models import JobListing, JobBoard


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
        """Initialize Playwright browser"""
        if self.browser is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            logger.info("Browser initialized")

    async def _close_browser(self):
        """Close Playwright browser"""
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
            page_jobs = await self._scrape_page(query, location, page_num, remote_only)

            if not page_jobs:
                logger.info(f"No more results on page {page_num}")
                break

            jobs.extend(page_jobs)
            page_num += 1

            # Random delay between pages
            await self._random_delay(2, 4)

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

        try:
            page = await self.browser.new_page()
            page.set_default_timeout(30000)

            # Navigate to search results
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)  # Wait for JavaScript

            # Get page content
            content = await page.content()
            await page.close()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            job_cards = soup.find_all('div', class_=re.compile(r'job_seen_beacon'))

            jobs = []
            for card in job_cards:
                try:
                    job = self._parse_job_card(card)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Failed to parse job card: {e}")
                    continue

            return jobs

        except Exception as e:
            logger.error(f"Failed to scrape page {page_num}: {e}")
            return []

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
