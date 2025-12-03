"""Indeed job board scraper using Playwright with Kameleo browser profiles"""
import asyncio
import json
import os
import random
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
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

# Pattern to extract mosaic data (embedded JSON with job listings)
MOSAIC_PATTERN = r'window\.mosaic\.providerData\["mosaic-provider-jobcards"\]\s*=\s*({.*?});'


class IndeedKameleoScraper(BaseScraper):
    """
    Indeed scraper using Playwright with Kameleo browser profiles for enhanced anti-detection.

    Features:
    - Real browser fingerprints via Kameleo
    - Mosaic JSON extraction (more reliable than DOM parsing)
    - Fallback to DOM parsing if mosaic data not available
    - Proxy support
    - Automatic browser reconnection on failures
    """

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

            # Step 4: Find or create Kameleo profile
            profile_name = "indeed-scraper-2"
            logger.info(f"Looking for existing profile '{profile_name}'...")
            
            try:
                # Search for existing profile by name
                profiles = await asyncio.to_thread(
                    self.kameleo_client.profile.list_profiles
                )
                
                existing_profile = None
                for profile in profiles:
                    if profile.name == profile_name:
                        existing_profile = profile
                        break
                
                if existing_profile:
                    logger.info(f"✅ Found existing profile '{profile_name}' (ID: {existing_profile.id})")
                    logger.info("Using profile as-is without modifications")
                    logger.info(f"Profile details:")
                    logger.info(f"  - Name: {existing_profile.name}")
                    logger.info(f"  - ID: {existing_profile.id}")
                    if hasattr(existing_profile, 'proxy') and existing_profile.proxy:
                        if hasattr(existing_profile.proxy, 'extra') and existing_profile.proxy.extra:
                            proxy_server = existing_profile.proxy.extra
                            logger.info(f"  - Proxy host: {proxy_server.host if hasattr(proxy_server, 'host') else 'N/A'}")
                            logger.info(f"  - Proxy port: {proxy_server.port if hasattr(proxy_server, 'port') else 'N/A'}")
                    else:
                        logger.info(f"  - Proxy configured: No")
                    self.kameleo_profile = existing_profile
                else:
                    logger.info(f"Profile '{profile_name}' not found, creating new one...")
                    create_profile_request = CreateProfileRequest(
                        fingerprint_id=fingerprint.id,
                        name=profile_name,
                    )

                    # Add proxy if configured
                    if proxy_choice:
                        create_profile_request.proxy = proxy_choice

                    self.kameleo_profile = await asyncio.to_thread(
                        self.kameleo_client.profile.create_profile,
                        create_profile_request
                    )
                    logger.info(f"✅ Created new Kameleo profile: {profile_name} (ID: {self.kameleo_profile.id})")
                    
            except Exception as e:
                logger.error(f"❌ Failed to find/create Kameleo profile: {e}")
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

        # Stop Kameleo profile (but don't delete it for reuse)
        if self.kameleo_client and self.kameleo_profile:
            try:
                logger.info("Stopping Kameleo profile...")
                await asyncio.to_thread(
                    self.kameleo_client.profile.stop_profile,
                    self.kameleo_profile.id
                )
                logger.info("✅ Kameleo profile stopped (preserved for reuse)")
            except Exception as e:
                logger.warning(f"Failed to stop Kameleo profile: {e}")

            self.kameleo_profile = None

        logger.info("Browser closed and Kameleo profile stopped")

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

            raw_json = match.group(1)
            logger.debug(f"Raw mosaic JSON extracted (length: {len(raw_json)} chars)")
            logger.debug(f"Raw mosaic JSON preview: {raw_json[:500]}...")

            data = json.loads(raw_json)
            # logger.debug(f"Parsed mosaic data keys: {list(data.keys())}")

            # Extract job results
            jobs_data = data.get('metaData', {}).get('mosaicProviderJobCardsModel', {})
            # logger.debug(f"Job cards model keys: {list(jobs_data.keys())}")

            jobs_list = jobs_data.get('results', [])
            logger.debug(f"Number of job results in raw data: {len(jobs_list)}")

            # Get total count from tier summaries
            tier_summaries = jobs_data.get('tierSummaries', [])
            total_count = sum(tier.get('jobCount', 0) for tier in tier_summaries)
            logger.debug(f"Tier summaries: {tier_summaries}")

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
            # Log raw job data for debugging (enable when needed)
            # logger.debug("=" * 80)
            # logger.debug("Raw mosaic job data:")
            # logger.debug(json.dumps(job_data, indent=2, default=str))
            # logger.debug("=" * 80)

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

            # Extract company page link for website extraction
            # Note: companyOverviewLink exists but lacks tracking parameters (campaignid, from, tk, fromjk)
            # These parameters are required to avoid bot detection on company pages
            # So we always need to visit the job detail page to get the properly parameterized URL
            #
            # Terminology:
            # - "company URL" = Indeed company detail page (e.g., indeed.com/cmp/Google)
            # - "company website" = Actual hiring company's website (e.g., www.google.com)
            company_overview_link = job_data.get('companyOverviewLink', '')

            # Check if company link is available
            has_company_link = bool(company_overview_link)

            job_listing = JobListing(
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
                company_website=None,  # Will be populated by _extract_company_website
            )

            # Set flag to extract company URL (Indeed company page) from job detail page
            # We always need to visit the job page because:
            # 1. If we have company link: need to get it with tracking parameters
            # 2. If we don't have company link: need to try extracting it from job page
            job_listing._needs_company_url = True
            if has_company_link:
                logger.debug(f"Company link found in mosaic, will extract full URL with params from job page")
            else:
                logger.debug(f"No company link in mosaic data, will attempt extraction from job page")

            # Log parsed fields
            # logger.debug("Parsed job fields:")
            # logger.debug(f"  job_key: {job_key}")
            # logger.debug(f"  title: {title}")
            # logger.debug(f"  company: {company}")
            # logger.debug(f"  location: {location}")
            # logger.debug(f"  remote_type: {remote_type}")
            # logger.debug(f"  date_str: {date_str}")
            # logger.debug(f"  posted_date: {posted_date}")
            # logger.debug(f"  salary_min: {salary_min}")
            # logger.debug(f"  salary_max: {salary_max}")
            # logger.debug(f"  description: {description[:100]}..." if len(description) > 100 else f"  description: {description}")
            # logger.debug(f"  url: {url}")

            return job_listing

        except Exception as e:
            logger.warning(f"Error parsing mosaic job: {e}")
            logger.exception("Full traceback:")
            return None

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
                    page_jobs = await self._scrape_page(
                        query, location, page_num, remote_only,
                        max_results=max_results,
                        current_count=len(jobs)
                    )
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
        remote_only: bool,
        max_results: int = None,
        current_count: int = 0
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
            delay = random.uniform(0.5, 1.0)
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

            # # Check for CAPTCHA first
            # if 'verify you' in content.lower() or 'captcha' in content.lower():
            #     logger.error("❌ CAPTCHA detected on Indeed page!")
            #     logger.error("Indeed is showing a verification challenge.")
            #     # Save HTML for inspection
            #     debug_file = f"debug_indeed_captcha_{page_num}.html"
            #     with open(debug_file, 'w', encoding='utf-8') as f:
            #         f.write(content)
            #     logger.error(f"💾 Saved page HTML to {debug_file} for inspection")
            #     return []

            # Try to extract from mosaic JSON first (more reliable)
            jobs_data, total_count = self._extract_jobs_from_mosaic(content)

            if jobs_data:
                jobs = []
                for job_data in jobs_data:
                    job = self._parse_mosaic_job(job_data)
                    if job:
                        jobs.append(job)

                logger.info(f"✅ Successfully extracted {len(jobs)} jobs from mosaic JSON on page {page_num}")

                # Limit jobs to process based on max_results to avoid unnecessary page loads
                if max_results is not None:
                    jobs_needed = max_results - current_count
                    if jobs_needed <= 0:
                        logger.info(f"Already have {current_count} jobs, skipping company website extraction")
                        return jobs[:jobs_needed]  # Return empty list or remaining needed

                    if len(jobs) > jobs_needed:
                        logger.info(f"Only processing company websites for first {jobs_needed} of {len(jobs)} jobs to respect max_results={max_results}")
                        jobs_to_process = jobs[:jobs_needed]
                    else:
                        jobs_to_process = jobs
                else:
                    jobs_to_process = jobs

                # Extract company websites for each job (only for jobs that will be returned)
                logger.info(f"Extracting company websites for {len(jobs_to_process)} jobs...")
                for idx, job in enumerate(jobs_to_process, 1):
                    logger.info(f"Job {idx}/{len(jobs)}: {job.title} at {job.company}")

                    # Add random delay before processing each job to avoid rate limiting
                    delay = random.uniform(3.0, 6.0)
                    logger.debug(f"  → Waiting {delay:.1f}s before processing next company...")
                    await asyncio.sleep(delay)

                    company_url = None

                    # Check if we have a company URL to extract from
                    if hasattr(job, '_company_url') and job._company_url:
                        company_url = job._company_url
                        logger.debug(f"  → Got company URL from job post: {company_url}")
                    elif hasattr(job, '_needs_company_url') and job._needs_company_url and job.url:
                        # Need to extract company URL from job page first
                        try:
                            logger.debug(f"  → Extracting company URL from job page...")
                            company_url = await self._extract_company_url_from_job_page(job.url)
                            if company_url:
                                logger.debug(f"  → Found company URL: {company_url}")
                            else:
                                logger.debug(f"  → No company URL found on job page")
                            # Add delay after job page visit
                            await asyncio.sleep(random.uniform(2.0, 4.0))
                        except Exception as e:
                            logger.warning(f"  → Failed to extract company URL from job page: {e}")
                    else:
                        logger.debug(f"  → No company URL available for this job")

                    # Now extract company website if we have a company URL
                    if company_url:
                        try:
                            company_website = await self._extract_company_website(company_url)
                            if company_website:
                                job.company_website = company_website
                                logger.info(f"  → Company website: {company_website}")
                            else:
                                logger.debug(f"  → No company website found")

                        except Exception as e:
                            logger.warning(f"  → Failed to extract company website: {e}")
                    else:
                        logger.debug(f"  → No company URL available")

                    # Clean up temporary attributes
                    if hasattr(job, '_company_url'):
                        delattr(job, '_company_url')
                    if hasattr(job, '_needs_company_url'):
                        delattr(job, '_needs_company_url')

                return jobs

            # Fallback to DOM parsing if mosaic not found
            logger.info("Mosaic JSON not found, falling back to DOM parsing...")
            soup = BeautifulSoup(content, 'html.parser')

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

            # Parse job cards from DOM
            jobs = []
            for card in job_cards:
                try:
                    job = self._parse_job_card(card)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Failed to parse job card: {e}")
                    continue

            logger.info(f"✅ Successfully parsed {len(jobs)} jobs from DOM on page {page_num}")

            # Limit jobs to process based on max_results to avoid unnecessary page loads
            if max_results is not None:
                jobs_needed = max_results - current_count
                if jobs_needed <= 0:
                    logger.info(f"Already have {current_count} jobs, skipping company website extraction")
                    return jobs[:jobs_needed]  # Return empty list or remaining needed

                if len(jobs) > jobs_needed:
                    logger.info(f"Only processing company websites for first {jobs_needed} of {len(jobs)} jobs to respect max_results={max_results}")
                    jobs_to_process = jobs[:jobs_needed]
                else:
                    jobs_to_process = jobs
            else:
                jobs_to_process = jobs

            # Extract company websites for each job (only for jobs that will be returned)
            logger.info(f"Extracting company websites for {len(jobs_to_process)} jobs...")
            for idx, job in enumerate(jobs_to_process, 1):
                logger.info(f"Job {idx}/{len(jobs)}: {job.title} at {job.company}")

                # Add random delay before processing each job to avoid rate limiting
                delay = random.uniform(3.0, 6.0)
                logger.debug(f"  → Waiting {delay:.1f}s before processing next company...")
                await asyncio.sleep(delay)

                company_url = None

                # Check if we have a company URL to extract from
                if hasattr(job, '_company_url') and job._company_url:
                    company_url = job._company_url
                elif job.url:
                    # Need to extract company URL from job page
                    try:
                        logger.debug(f"  → Extracting company URL from job page...")
                        company_url = await self._extract_company_url_from_job_page(job.url)
                        if company_url:
                            logger.debug(f"  → Found company URL: {company_url}")
                        else:
                            logger.debug(f"  → No company URL found on job page")
                        # Add delay after job page visit
                        await asyncio.sleep(random.uniform(2.0, 4.0))
                    except Exception as e:
                        logger.warning(f"  → Failed to extract company URL from job page: {e}")

                # Now extract company website if we have a company URL
                if company_url:
                    try:
                        company_website = await self._extract_company_website(company_url)
                        if company_website:
                            job.company_website = company_website
                            logger.info(f"  → Company website: {company_website}")
                        else:
                            logger.debug(f"  → No company website found")

                    except Exception as e:
                        logger.warning(f"  → Failed to extract company website: {e}")
                else:
                    logger.debug(f"  → No company URL available")

                # Clean up temporary attribute
                if hasattr(job, '_company_url'):
                    delattr(job, '_company_url')

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
            # Log raw card HTML
            # logger.debug("=" * 80)
            # logger.debug("Raw DOM job card HTML:")
            # logger.debug(str(card)[:1000] + ("..." if len(str(card)) > 1000 else ""))
            # logger.debug("=" * 80)

            # Extract title and URL
            title_elem = card.find('h2', class_='jobTitle')
            if not title_elem:
                logger.debug("No title element found with class 'jobTitle'")
                return None

            title_link = title_elem.find('a')
            if not title_link:
                logger.debug("No anchor tag found in title element")
                return None

            title = title_link.get_text(strip=True)
            job_key = title_link.get('data-jk') or title_link.get('id', '').replace('job_', '')
            url = f"{self.base_url}/viewjob?jk={job_key}" if job_key else ""

            # Extract company
            company_elem = card.find('span', {'data-testid': 'company-name'})
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"

            # Extract company URL if available
            company_url = None
            company_link = card.find('a', {'data-testid': 'company-name'}) or card.find('a', href=re.compile(r'/cmp/'))
            if company_link and company_link.get('href'):
                href = company_link.get('href')
                # Build full company URL
                if href.startswith('/cmp/'):
                    company_url = f"{self.base_url}{href}"
                elif 'indeed.com/cmp/' in href:
                    company_url = href

            # Extract location
            location_elem = card.find('div', {'data-testid': 'text-location'})
            location = location_elem.get_text(strip=True) if location_elem else "Remote"

            # Extract description snippet
            desc_elem = card.find('div', class_='job-snippet')
            description = desc_elem.get_text(strip=True) if desc_elem else ""

            # Extract posted date
            date_elem = card.find('span', class_='date')
            date_str = date_elem.get_text(strip=True) if date_elem else ""
            posted_date = self._parse_posted_date(date_str)

            # Extract salary if available
            salary_elem = card.find('div', class_=re.compile(r'salary-snippet'))
            salary_text = salary_elem.get_text(strip=True) if salary_elem else None

            job_listing = JobListing(
                id=job_key or None,
                title=title,
                company=company,
                location=location,
                description=description,
                url=url,
                posted_date=posted_date,
                board_source=JobBoard.INDEED,
                remote_type="Remote" if "remote" in location.lower() else None,
                scraped_at=datetime.now(),
                company_website=None,  # Will be populated later
            )

            # Store company URL temporarily for extraction
            if company_url:
                job_listing._company_url = company_url

            # Log parsed fields
            # logger.debug("Parsed DOM job fields:")
            # logger.debug(f"  job_key: {job_key}")
            # logger.debug(f"  title: {title}")
            # logger.debug(f"  company: {company}")
            # logger.debug(f"  location: {location}")
            # logger.debug(f"  date_str: {date_str}")
            # logger.debug(f"  posted_date: {posted_date}")
            # logger.debug(f"  salary_text: {salary_text}")
            # logger.debug(f"  description: {description[:100]}..." if len(description) > 100 else f"  description: {description}")
            # logger.debug(f"  url: {url}")

            return job_listing

        except Exception as e:
            logger.warning(f"Error parsing job card: {e}")
            logger.exception("Full traceback:")
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

    async def _extract_company_url_from_job_page(self, job_url: str) -> Optional[str]:
        """
        Extract Indeed company page URL (not the actual company website) with parameters from a job detail page.

        Terminology:
        - This extracts the Indeed company detail page URL (e.g., indeed.com/cmp/Google)
        - NOT the actual hiring company's website (e.g., www.google.com)
        - The company website is extracted later via _extract_company_website()

        Indeed requires specific tracking parameters (campaignid, from, tk, fromjk) on company URLs
        to avoid bot detection. These are dynamically generated on the job page.

        Args:
            job_url: URL to Indeed job page (e.g., https://www.indeed.com/viewjob?jk=abc123)

        Returns:
            Full Indeed company page URL with parameters (e.g., 'https://www.indeed.com/cmp/Company-Name?campaignid=...&from=...&tk=...&fromjk=...')
            or None if not found
        """
        page = None
        try:
            logger.debug(f"Extracting company URL from job page: {job_url}")

            # Create new page from context
            page = await self.context.new_page()
            page.set_default_timeout(15000)

            # Add small delay before navigation
            delay = random.uniform(1.0, 2.0)
            await page.wait_for_timeout(int(delay * 1000))

            # Navigate to job page
            response = await page.goto(job_url, wait_until='domcontentloaded', timeout=15000)

            if response.status >= 400:
                logger.warning(f"Job page returned status {response.status}: {job_url}")
                return None

            # Wait for content to load
            await page.wait_for_timeout(1000)

            # Get page content
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Look for company profile link with full parameters
            # Indeed shows company links with various patterns
            company_link_patterns = [
                soup.find('a', href=re.compile(r'/cmp/.*\?')),  # Links with query parameters
                soup.find('a', href=re.compile(r'/cmp/')),  # Links without parameters (fallback)
                soup.find('a', {'data-testid': re.compile(r'employer.*link', re.I)}),
                soup.find('div', {'data-testid': 'jobsearch-CompanyAvatar'}),
            ]

            for link_or_container in company_link_patterns:
                if not link_or_container:
                    continue

                # If it's a container, find the link inside
                if link_or_container.name == 'div':
                    link = link_or_container.find('a', href=True)
                else:
                    link = link_or_container

                if link and link.get('href'):
                    href = link.get('href')

                    # Build full URL if needed
                    if href.startswith('/cmp/'):
                        company_url = f"{self.base_url}{href}"
                    elif 'indeed.com/cmp/' in href:
                        company_url = href
                    else:
                        continue

                    # Log whether we found parameters
                    has_params = '?' in company_url
                    if has_params:
                        logger.debug(f"Found company URL with tracking parameters from job page: {company_url}")
                    else:
                        logger.debug(f"Found company URL without parameters from job page: {company_url}")

                    return company_url

            logger.debug(f"No company URL found on job page: {job_url}")
            return None

        except Exception as e:
            logger.warning(f"Error extracting company URL from job page {job_url}: {e}")
            return None
        finally:
            if page:
                await page.close()

    async def _extract_company_website(self, company_url: str) -> Optional[str]:
        """
        Extract company website domain from Indeed company page.

        Args:
            company_url: URL to Indeed company page (e.g., https://www.indeed.com/cmp/Company-Name)

        Returns:
            Company website domain (e.g., 'company.com') or None if not found
        """
        page = None
        try:
            logger.debug(f"Extracting company website from: {company_url}")

            # Create new page from context
            page = await self.context.new_page()
            page.set_default_timeout(20000)  # 20 second timeout for company pages

            # Add random delay before navigation to simulate human behavior
            delay = random.uniform(2.0, 4.0)
            logger.debug(f"  → Waiting {delay:.1f}s before navigating to company page...")
            await page.wait_for_timeout(int(delay * 1000))

            # Navigate to company page
            response = await page.goto(company_url, wait_until='domcontentloaded', timeout=20000)

            if response.status >= 400:
                logger.warning(f"Company page returned status {response.status}: {company_url}")
                return None

            # Wait for content to load with random delay
            content_load_delay = random.uniform(500, 1000)
            await page.wait_for_timeout(int(content_load_delay))

            # Get page content
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Strategy 1: Look for company website link with common patterns
            # Indeed typically shows company website in the "About" section or header
            website_patterns = [
                # Pattern 1: Link with data-testid="companyLink[]" inside companyInfo-companyWebsite
                soup.find('li', {'data-testid': 'companyInfo-companyWebsite'}),
                # Pattern 2: Link with specific text
                soup.find('a', string=re.compile(r'(company website|visit website|website)', re.I)),
                # Pattern 3: Link with data-testid containing "website"
                soup.find('a', {'data-testid': re.compile(r'website', re.I)}),
                # Pattern 4: Link in company info section
                soup.find('div', class_=re.compile(r'company.*info', re.I)),
            ]

            for pattern_result in website_patterns:
                if pattern_result:
                    # If it's a div or li, find links within it
                    if pattern_result.name in ['div', 'li']:
                        links = pattern_result.find_all('a', href=True)
                        for link in links:
                            href = link.get('href', '')
                            # Filter out Indeed internal links
                            if href and not any(x in href.lower() for x in ['indeed.com', 'javascript:', 'mailto:', '#']):
                                domain = self._extract_domain_from_url(href)
                                if domain:
                                    logger.info(f"✅ Found company website via pattern: {domain}")
                                    return domain
                    else:
                        # It's an anchor tag
                        href = pattern_result.get('href', '')
                        if href and not any(x in href.lower() for x in ['indeed.com', 'javascript:', 'mailto:', '#']):
                            domain = self._extract_domain_from_url(href)
                            if domain:
                                logger.info(f"✅ Found company website via link: {domain}")
                                return domain

            # Strategy 2: Look for external links (not indeed.com)
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')
                # Skip internal links, social media, and common non-website links
                skip_domains = [
                    'indeed.com', 'linkedin.com', 'facebook.com', 'twitter.com',
                    'instagram.com', 'youtube.com', 'glassdoor.com',
                    'javascript:', 'mailto:', '#', '/cmp/', '/jobs'
                ]

                if href and not any(x in href.lower() for x in skip_domains):
                    # Check if it looks like a company website
                    if href.startswith('http'):
                        domain = self._extract_domain_from_url(href)
                        if domain:
                            logger.info(f"✅ Found company website via external link: {domain}")
                            return domain

            # Strategy 3: Check for structured data (JSON-LD)
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        # Look for organization schema
                        if data.get('@type') == 'Organization':
                            url = data.get('url')
                            if url:
                                domain = self._extract_domain_from_url(url)
                                if domain:
                                    logger.info(f"✅ Found company website via JSON-LD: {domain}")
                                    return domain
                except:
                    continue

            logger.debug(f"No company website found on page: {company_url}")
            return None

        except Exception as e:
            logger.warning(f"Error extracting company website from {company_url}: {e}")
            return None
        finally:
            if page:
                await page.close()

    def _extract_domain_from_url(self, url: str) -> Optional[str]:
        """
        Extract clean domain from URL.

        Args:
            url: Full URL

        Returns:
            Domain (e.g., 'company.com') or None
        """
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path

            # Remove 'www.' prefix
            if domain.startswith('www.'):
                domain = domain[4:]

            # Basic validation - should have at least one dot
            if '.' not in domain:
                return None

            # Remove trailing slash or path components
            domain = domain.split('/')[0]

            return domain if domain else None

        except Exception as e:
            logger.debug(f"Error parsing domain from URL '{url}': {e}")
            return None

    async def get_job_details(self, job_url: str) -> Optional[JobListing]:
        """Get detailed job information (not implemented for MVP)"""
        logger.debug(f"Job details fetching not implemented for MVP: {job_url}")
        return None
