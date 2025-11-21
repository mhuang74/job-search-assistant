"""Indeed job board scraper using Crawl4AI for improved accuracy and anti-detection"""
import asyncio
import json
import os
import random
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode, quote_plus
from loguru import logger

from .base import BaseScraper
from ..models import JobListing, JobBoard

# Crawl4AI imports
try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
    from crawl4ai.extraction_strategy import JsonCssExtractionStrategy, LLMExtractionStrategy
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    logger.warning("crawl4ai not installed. Install with: pip install crawl4ai")


class IndeedCrawl4AIScraper(BaseScraper):
    """Indeed scraper using Crawl4AI for enhanced reliability and accuracy"""

    def __init__(self, config: dict = None):
        super().__init__(JobBoard.INDEED, config)
        self.base_url = "https://www.indeed.com"
        self.crawler: Optional[AsyncWebCrawler] = None

        if not CRAWL4AI_AVAILABLE:
            raise ImportError("crawl4ai is required. Install with: pip install crawl4ai")

        # Extraction strategy configuration
        self.extraction_mode = self.config.get('extraction_mode', 'css')  # 'css', 'llm', or 'hybrid'
        self.llm_provider = self.config.get('llm_provider', 'openai/gpt-4o-mini')

        # Initialize extraction strategies
        self.css_strategy = self._create_css_strategy()
        self.llm_strategy = None  # Lazy init when needed

    def _create_css_strategy(self) -> JsonCssExtractionStrategy:
        """Create CSS-based extraction strategy for Indeed job cards"""
        schema = {
            "name": "Indeed Job Listings",
            "baseSelector": "div.job_seen_beacon, div[data-testid='job-card'], div.jobsearch-ResultsList > div",
            "fields": [
                {
                    "name": "title",
                    "selector": "h2.jobTitle span, h2.jobTitle a span, a[data-jk] span",
                    "type": "text"
                },
                {
                    "name": "company",
                    "selector": "span[data-testid='company-name'], span.companyName",
                    "type": "text"
                },
                {
                    "name": "location",
                    "selector": "div[data-testid='text-location'], div.companyLocation",
                    "type": "text"
                },
                {
                    "name": "salary",
                    "selector": "div[class*='salary-snippet'], div[class*='salaryOnly'], div.salary-snippet-container",
                    "type": "text"
                },
                {
                    "name": "description",
                    "selector": "div.job-snippet, div[class*='job-snippet'], ul li",
                    "type": "text"
                },
                {
                    "name": "posted_date",
                    "selector": "span.date, span[class*='date']",
                    "type": "text"
                },
                {
                    "name": "job_key",
                    "selector": "a[data-jk]",
                    "type": "attribute",
                    "attribute": "data-jk"
                },
                {
                    "name": "job_url",
                    "selector": "h2.jobTitle a, a[data-jk]",
                    "type": "attribute",
                    "attribute": "href"
                },
                {
                    "name": "company_url",
                    "selector": "a[href*='/cmp/']",
                    "type": "attribute",
                    "attribute": "href"
                }
            ]
        }
        return JsonCssExtractionStrategy(schema=schema)

    def _create_llm_strategy(self) -> Optional[LLMExtractionStrategy]:
        """Create LLM-based extraction strategy for enhanced accuracy"""
        api_key = os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')

        if not api_key:
            logger.warning("No LLM API key found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY for LLM extraction.")
            return None

        # Determine provider based on available key
        if os.getenv('ANTHROPIC_API_KEY'):
            provider = "anthropic/claude-sonnet-4-20250514"
        else:
            provider = self.llm_provider

        schema = {
            "type": "object",
            "properties": {
                "jobs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Job title"},
                            "company": {"type": "string", "description": "Company name"},
                            "location": {"type": "string", "description": "Job location"},
                            "salary_min": {"type": "integer", "description": "Minimum salary in USD (annual)"},
                            "salary_max": {"type": "integer", "description": "Maximum salary in USD (annual)"},
                            "salary_text": {"type": "string", "description": "Original salary text"},
                            "description": {"type": "string", "description": "Job description snippet"},
                            "posted_date": {"type": "string", "description": "When posted (e.g., '2 days ago')"},
                            "is_remote": {"type": "boolean", "description": "Whether remote position"},
                            "job_key": {"type": "string", "description": "Indeed job key from data-jk attribute"}
                        },
                        "required": ["title", "company"]
                    }
                }
            }
        }

        try:
            from crawl4ai.config import LLMConfig
            return LLMExtractionStrategy(
                llm_config=LLMConfig(provider=provider, api_key=api_key),
                schema=schema,
                extraction_type="schema",
                instruction="""
                Extract all job listings from this Indeed search results page.
                For salary, parse ranges like "$50,000 - $70,000 a year" into min/max integers.
                Convert hourly rates to annual (hourly * 2080).
                For is_remote, check if location contains "Remote" or has remote badge.
                Extract job_key from the data-jk attribute on job card links.
                """
            )
        except Exception as e:
            logger.warning(f"Failed to create LLM strategy: {e}")
            return None

    def _get_browser_config(self) -> BrowserConfig:
        """Configure browser with anti-detection settings"""
        proxy = self.config.get('proxy') or os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')

        return BrowserConfig(
            browser_type=self.config.get('browser', 'chromium'),
            headless=self.config.get('headless', True),
            viewport_width=self.config.get('viewport_width', 1920),
            viewport_height=self.config.get('viewport_height', 1080),
            proxy=proxy,
            user_agent=self._get_random_user_agent(),
            extra_args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ]
        )

    def _get_crawler_config(self, use_llm: bool = False) -> CrawlerRunConfig:
        """Configure crawler run settings"""
        strategy = self.llm_strategy if use_llm and self.llm_strategy else self.css_strategy

        return CrawlerRunConfig(
            extraction_strategy=strategy,
            # Anti-detection settings
            simulate_user=True,
            override_navigator=True,
            magic=True,
            # Content handling
            wait_until="domcontentloaded",
            delay_before_return_html=2.0,
            # Caching
            cache_mode=CacheMode.BYPASS,
            # Session management
            session_id="indeed_scraper",
        )

    async def __aenter__(self):
        """Initialize crawler context"""
        self.crawler = AsyncWebCrawler(config=self._get_browser_config())
        await self.crawler.__aenter__()
        logger.info("[Crawl4AI] Browser initialized with anti-detection measures")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup crawler context"""
        if self.crawler:
            await self.crawler.__aexit__(exc_type, exc_val, exc_tb)
            self.crawler = None
            logger.info("[Crawl4AI] Browser closed")

    async def search(
        self,
        query: str,
        location: str = "Remote",
        max_results: int = 50,
        remote_only: bool = True
    ) -> List[JobListing]:
        """
        Search for jobs on Indeed using Crawl4AI

        Args:
            query: Job search query (e.g., "software engineer")
            location: Location filter (default: "Remote")
            max_results: Maximum number of results to return
            remote_only: Filter for remote jobs only

        Returns:
            List of JobListing objects
        """
        logger.info(f"[Crawl4AI] Searching Indeed: query='{query}', location='{location}', max_results={max_results}")

        # Initialize LLM strategy if needed
        if self.extraction_mode in ('llm', 'hybrid') and not self.llm_strategy:
            self.llm_strategy = self._create_llm_strategy()

        jobs = []
        page_num = 0
        max_pages = min((max_results // 15) + 1, 10)  # Indeed shows ~15 jobs per page
        consecutive_failures = 0
        max_consecutive_failures = 3

        while len(jobs) < max_results and page_num < max_pages:
            url = self._build_search_url(query, location, page_num, remote_only)
            logger.info(f"[Crawl4AI] Scraping page {page_num + 1}/{max_pages}: {url}")

            try:
                # Determine extraction strategy for this page
                use_llm = self.extraction_mode == 'llm'

                result = await self.crawler.arun(
                    url=url,
                    config=self._get_crawler_config(use_llm=use_llm)
                )

                if not result.success:
                    logger.warning(f"[Crawl4AI] Failed to fetch page: {result.error_message}")
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        logger.error(f"[Crawl4AI] {max_consecutive_failures} consecutive failures, stopping")
                        break
                    await asyncio.sleep(5)  # Wait before retry
                    continue

                consecutive_failures = 0  # Reset on success

                # Parse extraction results
                page_jobs = self._parse_extraction_result(result.extracted_content, use_llm)

                # Hybrid mode: retry with LLM if CSS extraction failed
                if self.extraction_mode == 'hybrid' and not page_jobs and self.llm_strategy:
                    logger.info("[Crawl4AI] CSS extraction failed, trying LLM extraction...")
                    result = await self.crawler.arun(
                        url=url,
                        config=self._get_crawler_config(use_llm=True)
                    )
                    if result.success:
                        page_jobs = self._parse_extraction_result(result.extracted_content, use_llm=True)

                if not page_jobs:
                    logger.info(f"[Crawl4AI] No jobs found on page {page_num + 1}, might be end of results")
                    # Check if we got any content at all
                    if result.html and len(result.html) < 5000:
                        logger.warning("[Crawl4AI] Page content very small, possible blocking")
                    break

                jobs.extend(page_jobs)
                logger.info(f"[Crawl4AI] Found {len(page_jobs)} jobs on page {page_num + 1} (total: {len(jobs)})")

                # Anti-detection delay between pages
                delay = random.uniform(4, 8)
                logger.debug(f"[Crawl4AI] Waiting {delay:.1f}s before next page...")
                await asyncio.sleep(delay)

                page_num += 1

            except Exception as e:
                logger.error(f"[Crawl4AI] Error scraping page {page_num + 1}: {type(e).__name__}: {e}")
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    break
                await asyncio.sleep(5)

        logger.info(f"[Crawl4AI] Search complete. Total jobs found: {len(jobs)}")
        return jobs[:max_results]

    def _build_search_url(
        self,
        query: str,
        location: str,
        page_num: int,
        remote_only: bool
    ) -> str:
        """Build Indeed search URL with filters"""
        params = {
            'q': query,
            'l': location,
            'start': page_num * 10,
        }

        if remote_only:
            params['sc'] = '0kf:attr(DSQF7);'  # Indeed's remote filter

        return f"{self.base_url}/jobs?{urlencode(params)}"

    def _parse_extraction_result(
        self,
        extracted_content: str,
        use_llm: bool = False
    ) -> List[JobListing]:
        """Convert Crawl4AI extraction results to JobListing objects"""
        if not extracted_content:
            return []

        try:
            data = json.loads(extracted_content)

            # Handle different response structures
            if use_llm and isinstance(data, dict) and 'jobs' in data:
                items = data['jobs']
            elif isinstance(data, list):
                items = data
            else:
                logger.warning(f"[Crawl4AI] Unexpected extraction format: {type(data)}")
                return []

            jobs = []
            for item in items:
                try:
                    job = self._item_to_job_listing(item)
                    if job and job.title:  # Only add jobs with at least a title
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[Crawl4AI] Failed to parse job item: {e}")
                    continue

            return jobs

        except json.JSONDecodeError as e:
            logger.error(f"[Crawl4AI] Failed to parse extracted content: {e}")
            return []

    def _item_to_job_listing(self, item: Dict[str, Any]) -> Optional[JobListing]:
        """Convert extraction item to JobListing object"""
        title = (item.get('title') or '').strip()
        if not title:
            return None

        company = (item.get('company') or 'Unknown').strip()
        location = (item.get('location') or 'Remote').strip()
        description = (item.get('description') or '').strip()

        # Build job URL
        job_key = item.get('job_key')
        job_url = item.get('job_url', '')
        if job_key and not job_url:
            job_url = f"{self.base_url}/viewjob?jk={job_key}"
        elif job_url and not job_url.startswith('http'):
            job_url = f"{self.base_url}{job_url}"

        # Parse posted date
        posted_date = self._parse_posted_date(item.get('posted_date', ''))

        # Parse salary
        salary_min, salary_max = self._parse_salary(item)

        # Determine remote status
        is_remote = item.get('is_remote', False) or 'remote' in location.lower()
        remote_type = 'Remote' if is_remote else None

        # Build company URL
        company_url = item.get('company_url')
        if company_url and not company_url.startswith('http'):
            company_url = f"{self.base_url}{company_url}"

        return JobListing(
            title=title,
            company=company,
            location=location,
            description=description,
            url=job_url,
            posted_date=posted_date,
            board_source=JobBoard.INDEED,
            company_website=company_url,  # Indeed company page for now
            salary_min=salary_min,
            salary_max=salary_max,
            remote_type=remote_type,
        )

    def _parse_posted_date(self, date_text: str) -> datetime:
        """Parse Indeed's relative date format (e.g., '2 days ago')"""
        if not date_text:
            return datetime.now()

        date_text = date_text.lower().strip()

        # Handle "PostedJust posted" or similar concatenated strings
        date_text = date_text.replace('posted', '').strip()

        if not date_text or date_text == "just" or 'today' in date_text:
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

    def _parse_salary(self, item: Dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
        """Parse salary information from extraction item"""
        # Check for pre-parsed values (from LLM extraction)
        if item.get('salary_min') is not None:
            return float(item['salary_min']), float(item.get('salary_max') or item['salary_min'])

        salary_text = item.get('salary') or item.get('salary_text') or ''
        if not salary_text:
            return None, None

        # Extract numbers from salary text
        # Handles: "$50,000 - $70,000 a year", "$25 - $35 an hour", "$80K - $100K"
        numbers = re.findall(r'\$?([\d,]+(?:\.\d{2})?)\s*[kK]?', salary_text)

        if not numbers:
            return None, None

        values = []
        for num in numbers:
            num_clean = num.replace(',', '')
            try:
                val = float(num_clean)
                # Check if it's in thousands (K notation)
                if 'k' in salary_text.lower() and val < 1000:
                    val *= 1000
                # Check if it's hourly (convert to annual)
                if 'hour' in salary_text.lower() and val < 500:
                    val *= 2080  # 40 hours * 52 weeks
                values.append(val)
            except ValueError:
                continue

        if len(values) >= 2:
            return min(values), max(values)
        elif len(values) == 1:
            return values[0], values[0]

        return None, None

    async def get_job_details(self, job_url: str) -> Optional[JobListing]:
        """
        Fetch full job details from individual job page

        This can be enhanced to extract full job descriptions using LLM
        """
        logger.debug(f"[Crawl4AI] get_job_details not fully implemented: {job_url}")
        return None

    async def extract_company_website(self, company_page_url: str) -> Optional[str]:
        """
        Extract company's actual website from Indeed company profile page

        Uses LLM extraction for more accurate results
        """
        if not company_page_url:
            return None

        # Ensure we have LLM strategy for this
        if not self.llm_strategy:
            self.llm_strategy = self._create_llm_strategy()

        if not self.llm_strategy:
            logger.warning("[Crawl4AI] No LLM strategy available for company website extraction")
            return await self._extract_company_website_css(company_page_url)

        try:
            from crawl4ai.config import LLMConfig

            # Create specialized extraction strategy for company pages
            company_schema = {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string"},
                    "website_url": {
                        "type": "string",
                        "description": "Company's official website URL (NOT indeed.com or linkedin.com)"
                    },
                    "industry": {"type": "string"},
                    "company_size": {"type": "string"},
                    "headquarters": {"type": "string"}
                }
            }

            api_key = os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
            provider = "anthropic/claude-sonnet-4-20250514" if os.getenv('ANTHROPIC_API_KEY') else self.llm_provider

            company_strategy = LLMExtractionStrategy(
                llm_config=LLMConfig(provider=provider, api_key=api_key),
                schema=company_schema,
                extraction_type="schema",
                instruction="""
                Find the company's official website URL from this Indeed company profile page.
                Look for:
                1. Links labeled "Website", "Company website", or "Visit website"
                2. External links in the company info section
                3. URLs mentioned in company description
                Do NOT return indeed.com, linkedin.com, glassdoor.com, or other job board URLs.
                Return the actual company domain (e.g., company.com).
                """
            )

            config = CrawlerRunConfig(
                extraction_strategy=company_strategy,
                magic=True,
                wait_until="domcontentloaded",
                delay_before_return_html=1.5,
            )

            result = await self.crawler.arun(url=company_page_url, config=config)

            if result.success and result.extracted_content:
                data = json.loads(result.extracted_content)
                website = data.get('website_url')
                if website and 'indeed.com' not in website.lower():
                    logger.info(f"[Crawl4AI] Extracted company website: {website}")
                    return website

        except Exception as e:
            logger.warning(f"[Crawl4AI] LLM extraction failed for company website: {e}")

        # Fallback to CSS extraction
        return await self._extract_company_website_css(company_page_url)

    async def _extract_company_website_css(self, company_page_url: str) -> Optional[str]:
        """Fallback CSS-based company website extraction"""
        try:
            schema = {
                "name": "Company Website",
                "baseSelector": "body",
                "fields": [
                    {
                        "name": "website_links",
                        "selector": "a[href]:not([href*='indeed.com']):not([href*='linkedin.com'])",
                        "type": "attribute",
                        "attribute": "href",
                        "multiple": True
                    }
                ]
            }

            config = CrawlerRunConfig(
                extraction_strategy=JsonCssExtractionStrategy(schema=schema),
                magic=True,
                wait_until="domcontentloaded",
            )

            result = await self.crawler.arun(url=company_page_url, config=config)

            if result.success and result.extracted_content:
                data = json.loads(result.extracted_content)
                links = data[0].get('website_links', []) if data else []

                # Filter for likely company websites
                for link in links:
                    if link and link.startswith('http') and \
                       'indeed.com' not in link and \
                       'linkedin.com' not in link and \
                       'glassdoor.com' not in link:
                        return link

        except Exception as e:
            logger.warning(f"[Crawl4AI] CSS extraction failed for company website: {e}")

        return None
