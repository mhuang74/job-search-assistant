# Implementation Techniques from Open Source Job Scrapers

This document extracts proven techniques and design patterns from successful open-source job scraping projects to inform our implementation.

## Reference Projects Analyzed

1. **JobSpy** (speedyapply/JobSpy) - 2.4k stars
   - Multi-board concurrent scraper (LinkedIn, Indeed, Glassdoor, ZipRecruiter, etc.)
   - Python 3.10+, uses requests + BeautifulSoup

2. **JobFunnel** (PaulMcInnis/JobFunnel) - 1.8k stars
   - Unified spreadsheet output with deduplication
   - YAML-based configuration, job progression tracking

3. **IndeedJobScraper** (Eben001/IndeedJobScraper)
   - Email notifications, screenshot capture
   - Multi-country support

4. **Scrythe** (greg-randall/scrythe)
   - Selenium stealth for anti-scraping mitigation
   - AI/LLM integration for content processing

5. **Luminati LinkedIn Scraper** (luminati-io/LinkedIn-Scraper)
   - Enterprise-grade proxy rotation
   - CAPTCHA handling patterns

---

## Key Architectural Patterns

### 1. Base Scraper Abstraction Pattern (from JobFunnel)

**Why it's valuable**: Enables consistent interface across different job boards while allowing board-specific customization.

**Implementation**:
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class JobBoard(Enum):
    INDEED = "indeed"
    LINKEDIN = "linkedin"
    REMOTEOK = "remoteok"
    WEWORKREMOTELY = "weworkremotely"

@dataclass
class JobListing:
    """Standardized job listing structure across all boards"""
    id: str  # Unique identifier (board-specific)
    title: str
    company: str
    location: str
    description: str
    url: str
    posted_date: datetime
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    job_type: Optional[str] = None  # Full-time, Part-time, Contract
    remote_type: Optional[str] = None  # Remote, Hybrid, On-site
    board_source: JobBoard = None
    scraped_at: datetime = None
    raw_html: Optional[str] = None  # Store for debugging

    def __post_init__(self):
        """Generate unique ID across boards for deduplication"""
        if not self.id:
            self.id = self.generate_id()

    def generate_id(self) -> str:
        """Create deterministic ID from job attributes"""
        import hashlib
        key = f"{self.company}:{self.title}:{self.location}".lower()
        return hashlib.md5(key.encode()).hexdigest()[:16]

class BaseScraper(ABC):
    """Base scraper with common functionality"""

    def __init__(self, board: JobBoard, config: dict):
        self.board = board
        self.config = config
        self.session = requests.Session()
        self._setup_session()

    def _setup_session(self):
        """Configure session with headers, retries, etc."""
        self.session.headers.update({
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })

        # Configure retries
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    @abstractmethod
    async def search(self, query: str, location: str = "",
                     filters: dict = None) -> List[JobListing]:
        """Search for jobs - must be implemented by subclass"""
        pass

    @abstractmethod
    async def get_job_details(self, job_url: str) -> JobListing:
        """Get detailed job information - must be implemented"""
        pass

    def _get_random_user_agent(self) -> str:
        """Rotate user agents to avoid detection"""
        from fake_useragent import UserAgent
        ua = UserAgent()
        return ua.random
```

### 2. Concurrent Multi-Board Scraping (from JobSpy)

**Why it's valuable**: Significantly reduces total scraping time by running scrapers in parallel.

**Implementation**:
```python
import asyncio
from typing import List, Dict

class JobScraperOrchestrator:
    """Orchestrate scraping across multiple job boards concurrently"""

    def __init__(self, scrapers: List[BaseScraper]):
        self.scrapers = scrapers

    async def scrape_all_boards(
        self,
        query: str,
        location: str = "",
        max_results_per_board: int = 100
    ) -> Dict[JobBoard, List[JobListing]]:
        """Scrape all boards concurrently"""

        tasks = [
            self._scrape_with_error_handling(
                scraper, query, location, max_results_per_board
            )
            for scraper in self.scrapers
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Organize results by board
        board_results = {}
        for scraper, result in zip(self.scrapers, results):
            if isinstance(result, Exception):
                logger.error(f"Error scraping {scraper.board}: {result}")
                board_results[scraper.board] = []
            else:
                board_results[scraper.board] = result

        return board_results

    async def _scrape_with_error_handling(
        self,
        scraper: BaseScraper,
        query: str,
        location: str,
        max_results: int
    ) -> List[JobListing]:
        """Wrap scraper with error handling and rate limiting"""
        try:
            # Add random delay to avoid simultaneous requests
            await asyncio.sleep(random.uniform(0, 2))

            jobs = await scraper.search(query, location)
            return jobs[:max_results]

        except Exception as e:
            logger.error(f"Failed to scrape {scraper.board}: {e}")
            raise

# Usage
async def main():
    scrapers = [
        IndeedScraper(JobBoard.INDEED, config),
        RemoteOKScraper(JobBoard.REMOTEOK, config),
        WeWorkRemotelyScraper(JobBoard.WEWORKREMOTELY, config),
    ]

    orchestrator = JobScraperOrchestrator(scrapers)
    all_jobs = await orchestrator.scrape_all_boards(
        query="senior software engineer",
        location="Remote"
    )

    print(f"Total jobs scraped: {sum(len(jobs) for jobs in all_jobs.values())}")
```

### 3. Smart Deduplication Strategy (from JobFunnel)

**Why it's valuable**: Same job often appears on multiple boards; avoid enriching duplicates.

**Implementation**:
```python
from typing import List, Set
from dataclasses import asdict

class JobDeduplicator:
    """Intelligent job deduplication across multiple boards"""

    @staticmethod
    def deduplicate_jobs(jobs: List[JobListing]) -> List[JobListing]:
        """
        Remove duplicate jobs using multiple matching strategies
        Priority: exact match > fuzzy match > keep all
        """
        unique_jobs = []
        seen_ids = set()
        seen_fuzzy = set()

        # Sort by scraped_at (newer first) to prefer fresh listings
        sorted_jobs = sorted(jobs, key=lambda j: j.scraped_at, reverse=True)

        for job in sorted_jobs:
            # Strategy 1: Exact ID match (company + title + location)
            if job.id in seen_ids:
                continue

            # Strategy 2: Fuzzy match (normalized title + company)
            fuzzy_key = JobDeduplicator._create_fuzzy_key(job)
            if fuzzy_key in seen_fuzzy:
                continue

            # Strategy 3: URL match (some boards cross-post with same URL)
            if JobDeduplicator._is_duplicate_url(job, unique_jobs):
                continue

            unique_jobs.append(job)
            seen_ids.add(job.id)
            seen_fuzzy.add(fuzzy_key)

        return unique_jobs

    @staticmethod
    def _create_fuzzy_key(job: JobListing) -> str:
        """Create normalized key for fuzzy matching"""
        import re

        # Normalize: lowercase, remove special chars, remove extra spaces
        def normalize(text: str) -> str:
            text = text.lower()
            text = re.sub(r'[^\w\s]', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text

        title = normalize(job.title)
        company = normalize(job.company)

        # Remove common variations
        title = title.replace('senior', 'sr').replace('junior', 'jr')
        title = title.replace('remote', '').replace('hybrid', '')

        return f"{company}:{title}"

    @staticmethod
    def _is_duplicate_url(job: JobListing, existing_jobs: List[JobListing]) -> bool:
        """Check if URL already exists (handles redirects)"""
        from urllib.parse import urlparse

        job_domain = urlparse(job.url).netloc
        job_path = urlparse(job.url).path

        for existing in existing_jobs:
            existing_domain = urlparse(existing.url).netloc
            existing_path = urlparse(existing.url).path

            # Same domain and very similar path = likely duplicate
            if job_domain == existing_domain and job_path == existing_path:
                return True

        return False
```

### 4. Rate Limiting & Pagination (from JobSpy insights)

**Why it's valuable**: Avoid getting blocked and handle platform-specific limits.

**Key insights from JobSpy**:
- **Indeed**: No rate limiting (best for scraping)
- **LinkedIn**: Rate limits around 10th page with single IP
- **All boards**: Cap around 1000 jobs per search

**Implementation**:
```python
import time
from typing import Optional
from dataclasses import dataclass

@dataclass
class RateLimitConfig:
    """Board-specific rate limiting configuration"""
    requests_per_minute: int
    max_pages: int
    delay_between_pages: float
    max_results: int

class RateLimiter:
    """Adaptive rate limiter with backoff"""

    # Board-specific configurations
    CONFIGS = {
        JobBoard.INDEED: RateLimitConfig(
            requests_per_minute=60,
            max_pages=100,
            delay_between_pages=1.0,
            max_results=1000
        ),
        JobBoard.LINKEDIN: RateLimitConfig(
            requests_per_minute=10,
            max_pages=10,  # Strict limit
            delay_between_pages=3.0,
            max_results=200
        ),
        JobBoard.REMOTEOK: RateLimitConfig(
            requests_per_minute=30,
            max_pages=50,
            delay_between_pages=2.0,
            max_results=500
        ),
    }

    def __init__(self, board: JobBoard):
        self.board = board
        self.config = self.CONFIGS.get(board, self._default_config())
        self.request_times = []

    async def wait_if_needed(self):
        """Wait if we're exceeding rate limits"""
        now = time.time()

        # Remove requests older than 1 minute
        self.request_times = [
            t for t in self.request_times
            if now - t < 60
        ]

        # Check if we've hit the limit
        if len(self.request_times) >= self.config.requests_per_minute:
            sleep_time = 60 - (now - self.request_times[0])
            if sleep_time > 0:
                logger.info(f"Rate limit reached for {self.board}, sleeping {sleep_time:.1f}s")
                await asyncio.sleep(sleep_time)

        # Add jitter to avoid detection patterns
        await asyncio.sleep(random.uniform(0.5, 1.5))

        self.request_times.append(time.time())

    @staticmethod
    def _default_config() -> RateLimitConfig:
        return RateLimitConfig(
            requests_per_minute=20,
            max_pages=20,
            delay_between_pages=2.0,
            max_results=400
        )

class PaginationHandler:
    """Handle pagination with rate limiting"""

    def __init__(self, scraper: BaseScraper, rate_limiter: RateLimiter):
        self.scraper = scraper
        self.rate_limiter = rate_limiter

    async def scrape_all_pages(
        self,
        query: str,
        location: str,
        max_results: Optional[int] = None
    ) -> List[JobListing]:
        """Scrape multiple pages with rate limiting"""
        all_jobs = []
        page = 0

        max_results = max_results or self.rate_limiter.config.max_results
        max_pages = self.rate_limiter.config.max_pages

        while page < max_pages and len(all_jobs) < max_results:
            # Rate limit before request
            await self.rate_limiter.wait_if_needed()

            try:
                jobs = await self.scraper.search(
                    query=query,
                    location=location,
                    page=page
                )

                if not jobs:
                    logger.info(f"No more results on page {page}")
                    break

                all_jobs.extend(jobs)
                page += 1

                logger.info(f"Scraped page {page}, total jobs: {len(all_jobs)}")

            except Exception as e:
                logger.error(f"Error on page {page}: {e}")
                # Exponential backoff on error
                await asyncio.sleep(2 ** page)
                break

        return all_jobs[:max_results]
```

### 5. Selenium Stealth Mode (from Scrythe)

**Why it's valuable**: Bypass bot detection on sophisticated platforms.

**Implementation**:
```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager

class StealthBrowser:
    """Browser with anti-detection measures"""

    @staticmethod
    def create_stealth_driver() -> webdriver.Chrome:
        """Create Chrome driver with stealth configuration"""

        chrome_options = Options()

        # Headless mode (optional)
        # chrome_options.add_argument("--headless=new")

        # Anti-detection arguments
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--dns-prefetch-disable")
        chrome_options.add_argument("--disable-browser-side-navigation")

        # Set realistic viewport
        chrome_options.add_argument("--window-size=1920,1080")

        # Disable automation flags
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # User agent
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        # Create driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Apply selenium-stealth
        stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )

        # Additional JavaScript to mask automation
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            """
        })

        return driver

# Usage
class LinkedInScraperWithStealth(BaseScraper):
    """LinkedIn scraper using stealth browser"""

    def __init__(self, board: JobBoard, config: dict):
        super().__init__(board, config)
        self.driver = StealthBrowser.create_stealth_driver()

    async def search(self, query: str, location: str = "") -> List[JobListing]:
        """Search with stealth browser"""
        url = f"https://www.linkedin.com/jobs/search/?keywords={query}"

        self.driver.get(url)
        await asyncio.sleep(random.uniform(2, 4))  # Human-like delay

        # Scroll to load dynamic content
        await self._smooth_scroll()

        # Extract jobs
        # ... implementation

    async def _smooth_scroll(self):
        """Scroll page smoothly like a human"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        while True:
            # Scroll down in chunks (human-like)
            for i in range(0, last_height, random.randint(100, 300)):
                self.driver.execute_script(f"window.scrollTo(0, {i});")
                await asyncio.sleep(random.uniform(0.1, 0.3))

            await asyncio.sleep(random.uniform(1, 2))

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
```

### 6. Configuration Management (from JobFunnel)

**Why it's valuable**: YAML configuration makes it easy to manage searches without code changes.

**Implementation**:
```yaml
# config/search_config.yaml
job_searches:
  - name: "Senior Software Engineer - Remote"
    query: "senior software engineer"
    location: "Remote"
    boards:
      - indeed
      - remoteok
      - weworkremotely
    filters:
      remote_only: true
      min_salary: 120000
      job_types:
        - Full-time
        - Contract
      posted_within_days: 7

  - name: "Data Engineer - Taiwan Team"
    query: "data engineer"
    location: ""
    boards:
      - linkedin
      - indeed
    filters:
      remote_only: true
      requires_enrichment: true
      min_taiwan_team_members: 1

linkedin_enrichment:
  service: "peopledatalabs"  # or "coresignal"
  cache_days: 30
  min_taiwan_team_members: 1
  target_industries:
    - Technology
    - SaaS
    - Fintech
  target_company_sizes:
    - "11-50"
    - "51-200"
    - "201-500"

ranking:
  weights:
    taiwan_team_count: 10
    same_city_count: 5
    industry_match: 3
    company_size_match: 3
    recency: 5

output:
  format: csv  # csv, json, excel
  path: "data/jobs"
  filename_template: "jobs_{date}_{query}.csv"

notifications:
  enabled: true
  email:
    to: "your@email.com"
    subject: "New Jobs Found: {count} matches"
    send_when: "new_jobs_only"  # always, new_jobs_only, never
```

**Python loader**:
```python
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class SearchConfig:
    name: str
    query: str
    location: str
    boards: List[str]
    filters: Dict

@dataclass
class AppConfig:
    job_searches: List[SearchConfig]
    linkedin_enrichment: Dict
    ranking: Dict
    output: Dict
    notifications: Dict

class ConfigLoader:
    """Load and validate YAML configuration"""

    @staticmethod
    def load(config_path: str = "config/search_config.yaml") -> AppConfig:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)

        # Parse job searches
        searches = [
            SearchConfig(**search)
            for search in data.get('job_searches', [])
        ]

        return AppConfig(
            job_searches=searches,
            linkedin_enrichment=data.get('linkedin_enrichment', {}),
            ranking=data.get('ranking', {}),
            output=data.get('output', {}),
            notifications=data.get('notifications', {})
        )
```

### 7. Email Notifications (from IndeedJobScraper)

**Why it's valuable**: Get notified immediately when relevant jobs are found.

**Implementation**:
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

class JobNotifier:
    """Send email notifications for job matches"""

    def __init__(self, config: Dict):
        self.config = config
        self.smtp_server = config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.from_email = config.get('from_email')
        self.password = config.get('password')  # Use app password, not account password

    def send_job_alert(
        self,
        to_email: str,
        jobs: List[JobListing],
        enriched_jobs: List[EnrichedJob] = None,
        csv_path: Optional[str] = None
    ):
        """Send email with job results"""

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Job Alert: {len(jobs)} new matches found"
        msg['From'] = self.from_email
        msg['To'] = to_email

        # Create HTML email body
        html_body = self._create_html_email(jobs, enriched_jobs)
        msg.attach(MIMEText(html_body, 'html'))

        # Attach CSV if provided
        if csv_path and Path(csv_path).exists():
            with open(csv_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename={Path(csv_path).name}'
                )
                msg.attach(part)

        # Send email
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.from_email, self.password)
                server.send_message(msg)
            logger.info(f"Email sent successfully to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

    def _create_html_email(
        self,
        jobs: List[JobListing],
        enriched_jobs: Optional[List[EnrichedJob]] = None
    ) -> str:
        """Create HTML formatted email"""

        # Sort by Taiwan team count if enriched
        if enriched_jobs:
            sorted_jobs = sorted(
                enriched_jobs,
                key=lambda j: (j.taiwan_team_count, j.posted_date),
                reverse=True
            )
            display_jobs = sorted_jobs[:10]  # Top 10
        else:
            display_jobs = jobs[:10]

        html = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; }
                .job-card {
                    border: 1px solid #ddd;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 5px;
                }
                .job-title {
                    font-size: 18px;
                    font-weight: bold;
                    color: #2557a7;
                }
                .company { font-size: 16px; color: #333; }
                .taiwan-badge {
                    background: #4CAF50;
                    color: white;
                    padding: 3px 8px;
                    border-radius: 3px;
                    font-size: 12px;
                }
            </style>
        </head>
        <body>
            <h2>🎯 New Job Matches Found</h2>
            <p>Found <strong>{total_count}</strong> jobs. Showing top {show_count}:</p>
        """.format(total_count=len(jobs), show_count=len(display_jobs))

        for job in display_jobs:
            taiwan_count = getattr(job, 'taiwan_team_count', 0)
            taiwan_badge = ""
            if taiwan_count > 0:
                taiwan_badge = f'<span class="taiwan-badge">🇹🇼 {taiwan_count} team members in Taiwan</span>'

            html += f"""
            <div class="job-card">
                <div class="job-title">{job.title}</div>
                <div class="company">{job.company} - {job.location}</div>
                {taiwan_badge}
                <p>{job.description[:200]}...</p>
                <a href="{job.url}">View Job</a>
            </div>
            """

        html += """
        </body>
        </html>
        """

        return html
```

### 8. Proxy Rotation Strategy (from Luminati insights)

**Why it's valuable**: Avoid IP bans when scraping at scale.

**Implementation**:
```python
from itertools import cycle
from typing import List, Optional

class ProxyRotator:
    """Rotate through proxies to avoid detection"""

    def __init__(self, proxy_list: Optional[List[str]] = None):
        """
        proxy_list format: ['http://user:pass@proxy1:port', ...]
        """
        self.proxy_list = proxy_list or []
        self.proxy_cycle = cycle(self.proxy_list) if self.proxy_list else None
        self.current_proxy = None
        self.failed_proxies = set()

    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Get next working proxy"""
        if not self.proxy_cycle:
            return None

        # Try up to len(proxy_list) proxies
        for _ in range(len(self.proxy_list)):
            proxy = next(self.proxy_cycle)

            if proxy not in self.failed_proxies:
                self.current_proxy = proxy
                return {
                    'http': proxy,
                    'https': proxy
                }

        # All proxies failed
        logger.warning("All proxies failed, using no proxy")
        return None

    def mark_proxy_failed(self, proxy: str):
        """Mark proxy as failed"""
        self.failed_proxies.add(proxy)
        logger.warning(f"Proxy marked as failed: {proxy}")

    def reset_failed_proxies(self):
        """Reset failed proxy list (for retry)"""
        self.failed_proxies.clear()

# Integration with scraper
class ScraperWithProxyRotation(BaseScraper):
    """Scraper that rotates proxies on failure"""

    def __init__(self, board: JobBoard, config: dict, proxy_list: List[str] = None):
        super().__init__(board, config)
        self.proxy_rotator = ProxyRotator(proxy_list)

    async def _make_request(self, url: str, max_retries: int = 3) -> requests.Response:
        """Make request with automatic proxy rotation on failure"""

        for attempt in range(max_retries):
            proxy = self.proxy_rotator.get_next_proxy()

            try:
                response = await asyncio.to_thread(
                    self.session.get,
                    url,
                    proxies=proxy,
                    timeout=10
                )

                # Check for blocks (status 999 for LinkedIn, 429 for rate limit)
                if response.status_code in [429, 999, 403]:
                    logger.warning(f"Blocked with status {response.status_code}")
                    if proxy:
                        self.proxy_rotator.mark_proxy_failed(proxy['http'])
                    continue

                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if proxy:
                    self.proxy_rotator.mark_proxy_failed(proxy['http'])

                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        raise Exception(f"Failed to fetch {url} after {max_retries} attempts")
```

---

## Recommended Library Choices

Based on the analysis of successful projects:

### For Job Scraping:
- **Playwright** (Modern, async) > **Selenium** (Stealth mode) > **Requests + BeautifulSoup** (Fastest)
- Use Playwright for JavaScript-heavy sites
- Use Requests for simple API-like endpoints

### For HTML Parsing:
- **BeautifulSoup4** (Most popular) or **Parsel** (Faster)
- **lxml** as parser (faster than html.parser)

### For Data Processing:
- **Pandas** for CSV/Excel export and data manipulation
- **SQLAlchemy** for database ORM

### For Configuration:
- **PyYAML** for config files
- **Pydantic** for validation
- **python-dotenv** for secrets

### For Anti-Detection:
- **selenium-stealth** for Selenium stealth mode
- **fake-useragent** for user agent rotation
- **undetected-chromedriver** as alternative to selenium-stealth

### For Async Operations:
- **asyncio** (built-in) for concurrent scraping
- **aiohttp** or **httpx** for async HTTP requests

---

## Implementation Priority for Our Project

### Phase 1: MVP (Week 1-2)
1. ✅ Base scraper abstraction with Indeed scraper
2. ✅ YAML configuration support
3. ✅ SQLite storage with job deduplication
4. ✅ CLI interface

### Phase 2: Multi-Board (Week 3)
1. ✅ Add RemoteOK and WeWorkRemotely scrapers
2. ✅ Concurrent scraping orchestrator
3. ✅ Rate limiting per board
4. ✅ CSV export

### Phase 3: LinkedIn Enrichment (Week 4)
1. ✅ Coresignal/People Data Labs integration
2. ✅ Company matching algorithm
3. ✅ Taiwan team member extraction
4. ✅ Caching layer

### Phase 4: Production Features (Week 5-6)
1. ✅ Email notifications
2. ✅ Proxy rotation (optional, for scale)
3. ✅ Selenium stealth mode (if needed for LinkedIn Jobs)
4. ✅ Web dashboard (FastAPI + React)

---

## Key Learnings & Best Practices

### 1. Rate Limiting is Critical
- Indeed: No rate limiting (scrape freely)
- LinkedIn: Very strict (10 pages max per IP)
- Always implement board-specific rate limiters

### 2. Deduplication Saves API Costs
- Same job appears on 3-5 boards on average
- Dedupe BEFORE enrichment to save 60-70% on API costs

### 3. Error Handling & Retries
- Sites change structure frequently
- Implement exponential backoff
- Log failures for debugging

### 4. User Agent Rotation
- Rotate user agents to appear as different browsers
- Use realistic, recent user agent strings

### 5. Respect robots.txt
- Check robots.txt before scraping
- Follow crawl-delay directives
- Use politeness delays even if not specified

### 6. Stealth Mode When Needed
- LinkedIn, Glassdoor require stealth measures
- Indeed, RemoteOK work fine with basic requests

### 7. Start Simple, Add Complexity
- Begin with Requests + BeautifulSoup
- Add Playwright only if JavaScript rendering needed
- Add Selenium stealth only if getting blocked

---

## Code Quality & Testing

### Unit Tests (from successful projects)
```python
# tests/test_deduplicator.py
import pytest
from your_app.deduplicator import JobDeduplicator
from your_app.models import JobListing

def test_exact_duplicate_removal():
    """Test that exact duplicates are removed"""
    job1 = JobListing(
        title="Software Engineer",
        company="Acme Corp",
        location="Remote",
        description="...",
        url="https://indeed.com/job1",
        posted_date=datetime.now(),
        board_source=JobBoard.INDEED
    )

    job2 = JobListing(
        title="Software Engineer",
        company="Acme Corp",
        location="Remote",
        description="Different description",
        url="https://linkedin.com/job2",
        posted_date=datetime.now(),
        board_source=JobBoard.LINKEDIN
    )

    unique = JobDeduplicator.deduplicate_jobs([job1, job2])
    assert len(unique) == 1

def test_fuzzy_duplicate_removal():
    """Test fuzzy matching (Sr. vs Senior)"""
    job1 = JobListing(
        title="Senior Software Engineer (Remote)",
        company="Acme Corp",
        location="Remote",
        # ...
    )

    job2 = JobListing(
        title="Sr. Software Engineer - Remote",
        company="Acme Corp",
        location="Remote",
        # ...
    )

    unique = JobDeduplicator.deduplicate_jobs([job1, job2])
    assert len(unique) == 1
```

---

## Performance Benchmarks (from JobSpy)

Expected scraping speeds:
- **Indeed**: 100 jobs in ~10 seconds (no rate limiting)
- **RemoteOK**: 50 jobs in ~8 seconds
- **LinkedIn**: 20 jobs in ~30 seconds (strict rate limiting)
- **WeWorkRemotely**: 30 jobs in ~5 seconds

**Concurrent scraping** (4 boards in parallel): ~40 seconds total vs. ~53 seconds sequential

---

## Security & Privacy

### 1. Credentials Management
```python
# Use environment variables, never commit credentials
from dotenv import load_dotenv
import os

load_dotenv()

SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
PEOPLEDATALABS_API_KEY = os.getenv('PEOPLEDATALABS_API_KEY')
```

### 2. Data Retention
```python
# Auto-delete old job listings
def cleanup_old_jobs(days: int = 30):
    """Delete jobs older than X days"""
    cutoff = datetime.now() - timedelta(days=days)
    session.query(Job).filter(Job.scraped_at < cutoff).delete()
    session.commit()
```

### 3. Respect Privacy
- Only scrape public job listings
- Don't scrape personal contact information
- Follow GDPR guidelines for EU data

---

## Additional Resources

- **JobSpy**: https://github.com/speedyapply/JobSpy
- **JobFunnel**: https://github.com/PaulMcInnis/JobFunnel
- **IndeedJobScraper**: https://github.com/Eben001/IndeedJobScraper
- **Scrythe**: https://github.com/greg-randall/scrythe
- **Luminati LinkedIn Scraper**: https://github.com/luminati-io/LinkedIn-Scraper

---

**Last Updated**: 2025-11-19
**Version**: 1.0
