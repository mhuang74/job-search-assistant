# Job Search Assistant - System Design Specification

## Executive Summary

A system to scrape remote job listings from job boards, enrich them with LinkedIn company data, and rank positions based on team presence in Taiwan. The system prioritizes cost-effectiveness, reliability, and maintainability while balancing custom development with third-party services.

## Requirements

### Functional Requirements
1. **Job Scraping**: Extract remote job listings from multiple job boards (Indeed, SimplyHired, etc.)
2. **Company Filtering**: Filter by industry, team location, team size
3. **LinkedIn Enrichment**: Retrieve company profiles and identify team members in Taiwan
4. **Intelligent Ranking**: Score jobs based on Taiwan team member count and proximity
5. **Data Persistence**: Store jobs, companies, and enrichment data
6. **Deduplication**: Handle same job across multiple boards

### Non-Functional Requirements
- **Scalability**: Handle 100-1000 jobs per search
- **Cost Efficiency**: Minimize API costs while maintaining reliability
- **Resilience**: Handle rate limits, CAPTCHAs, and site changes
- **Maintainability**: Clear separation of concerns, easy to update scrapers
- **Privacy**: Respect robots.txt and rate limits

## Recommended Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Orchestrator Layer                       │
│                  (Job Search Coordinator)                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
┌────────────┐  ┌────────────┐  ┌────────────┐
│ Job Board  │  │  LinkedIn  │  │  Ranking   │
│  Scraper   │  │ Enrichment │  │   Engine   │
└──────┬─────┘  └─────┬──────┘  └─────┬──────┘
       │              │               │
       ▼              ▼               ▼
┌─────────────────────────────────────────────┐
│          Data Layer (SQLite/PostgreSQL)     │
└─────────────────────────────────────────────┘
```

## Technology Stack Recommendations

### Core Language: **Python 3.10+**
**Rationale**:
- Excellent scraping libraries ecosystem
- Strong data processing capabilities (pandas)
- Good async support for parallel operations
- Your preferred choice aligns with best practices

### Component Breakdown

#### 1. Job Board Scraping

**Recommended Hybrid Approach**:

##### Option A: Custom Scraper (Primary) - **70% of traffic**
**Tech Stack**:
- **Playwright** (preferred over Selenium/ChromeDriver)
- **httpx** for faster API-like endpoints
- **BeautifulSoup4** or **Parsel** for parsing

**Rationale**:
- Playwright is faster, more reliable, and better maintained than Selenium
- Native async support for parallel scraping
- Better handling of modern JavaScript-heavy sites
- Excellent debugging tools and screenshots on failure
- Smaller resource footprint

**Libraries**:
```python
playwright==1.40.0
beautifulsoup4==4.12.2
httpx==0.25.2
parsel==1.8.1
```

**Use for**:
- Initial development and testing
- Job boards with simpler structure
- When you need full control
- Cost-sensitive scenarios

##### Option B: Paid API (Fallback/Supplement) - **30% of traffic**
**Recommended**: **ScraperAPI** or **Decodo Indeed Scraper**

**Comparison**:

| Service | Pros | Cons | Cost |
|---------|------|------|------|
| **ScraperAPI** | - Handles all job boards<br>- CAPTCHA solving<br>- Rotating proxies<br>- Geotargeting | - $49-149/mo<br>- Usage limits | 1000 calls: $49/mo |
| **Decodo Indeed Scraper** | - Indeed-specific<br>- Structured data<br>- No parsing needed | - Only Indeed<br>- $0.01-0.03/job | ~$10-30/mo for 1000 jobs |
| **Bright Data** | - Enterprise grade<br>- All sites | - Expensive<br>- Complex setup | $500+/mo |
| **Oxylabs** | - High quality<br>- LinkedIn support | - Very expensive | $600+/mo |

**Recommendation**:
- Start with **custom Playwright** for development
- Add **ScraperAPI** as fallback for CAPTCHA/blocks ($49/mo plan)
- Consider **Decodo** only if Indeed is primary source

**Hybrid Strategy**:
```python
# Pseudocode
def scrape_jobs(board, query):
    try:
        return custom_scraper.scrape(board, query)
    except (CaptchaDetected, RateLimited, Blocked):
        logger.info(f"Falling back to API for {board}")
        return scraper_api.scrape(board, query)
```

#### 2. LinkedIn Data Enrichment

**Recommended Approach**: **Paid API (Primary)**

**Option A: Proxycurl** (Recommended)
- **Cost**: $0.01-0.05 per company profile
- **Pros**:
  - Real-time LinkedIn data
  - Employee search with location filters
  - Company size, industry, headquarters
  - No risk of LinkedIn account ban
  - Reliable structured data
- **Cons**:
  - Recurring costs
  - Usage-based pricing

**Endpoint Usage**:
```python
# Company Profile: $0.01/call
GET /api/linkedin/company

# Employee Search with Taiwan filter: $0.03/call
GET /api/linkedin/company/employees/?country=Taiwan

# Budget estimate:
# 100 jobs × $0.04 = $4.00
# 1000 jobs × $0.04 = $40.00
```

**Option B: Custom LinkedIn Scraper** (Not Recommended)
- **Cons**:
  - High risk of account suspension
  - Requires maintaining cookies/sessions
  - CAPTCHA challenges
  - Rate limiting
  - Frequent site structure changes
  - Legal gray area (TOS violation)
- **Pros**:
  - No per-call costs

**Verdict**: **Use Proxycurl**. LinkedIn actively blocks scrapers, and the cost ($0.04/job) is reasonable compared to development time and risk.

**Alternative**: **PhantomBuster** ($30-$128/mo) if you need more LinkedIn automation, but Proxycurl is cleaner for this use case.

#### 3. Data Storage

**Recommended**: **PostgreSQL** (local or cloud)

**Schema Design**:
```sql
-- Jobs table
jobs (
    id, title, company_name, url, board_source,
    description, location, posted_date, scraped_at,
    company_id FK
)

-- Companies table
companies (
    id, name, linkedin_url, industry, size,
    headquarters_location, enriched_at
)

-- Team members table
team_members (
    id, company_id FK, name, title, location,
    country, city, linkedin_url
)

-- Rankings table
job_rankings (
    job_id FK, taiwan_team_count, ranking_score,
    proximity_score, calculated_at
)
```

**Alternative for MVP**: **SQLite**
- Simpler setup
- Good for < 10,000 jobs
- Easy to migrate to PostgreSQL later

**Library**:
```python
sqlalchemy==2.0.23  # ORM
alembic==1.13.0     # Migrations
```

#### 4. Ranking Engine

**Custom Algorithm** (Python)

**Scoring Factors**:
```python
def calculate_job_score(job):
    score = 0

    # Taiwan team members (highest weight)
    score += job.taiwan_team_count * 10

    # Team proximity to your city
    score += job.team_in_same_city * 5

    # Company size match
    if job.company_size in target_size_range:
        score += 3

    # Industry match
    if job.industry in target_industries:
        score += 3

    # Recent posting (decay function)
    days_old = (today - job.posted_date).days
    score += max(0, 5 - (days_old / 7))

    return score
```

**Library**: Custom logic with `pandas` for data manipulation

#### 5. Orchestration & Workflow

**Recommended**: **Celery** + **Redis** (for production) or **simple queue** (for MVP)

**For MVP**:
```python
# Simple async with asyncio
import asyncio

async def main():
    jobs = await scrape_all_boards()
    enriched = await enrich_with_linkedin(jobs)
    ranked = rank_jobs(enriched)
    save_to_db(ranked)
```

**For Production**:
```python
# Celery tasks
@celery.task
def scrape_indeed():
    ...

@celery.task
def enrich_company(company_id):
    ...
```

#### 6. Monitoring & Logging

**Libraries**:
```python
loguru==0.7.2           # Better logging
sentry-sdk==1.38.0      # Error tracking (free tier)
```

## Detailed Component Design

### 1. Job Board Scraper Module

**Supported Boards** (Priority order):
1. **Indeed** - Largest job board, good remote filter
2. **LinkedIn Jobs** - High quality, integrated with company data
3. **RemoteOK** - Remote-first, tech jobs
4. **We Work Remotely** - Curated remote jobs
5. **SimplyHired** - Good coverage

**Base Scraper Interface**:
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

@dataclass
class JobListing:
    title: str
    company: str
    url: str
    description: str
    location: str
    posted_date: datetime
    source: str

class JobBoardScraper(ABC):
    @abstractmethod
    async def search(self, query: str, filters: dict) -> List[JobListing]:
        pass

    @abstractmethod
    async def get_job_details(self, url: str) -> JobListing:
        pass

class IndeedScraper(JobBoardScraper):
    def __init__(self, use_api: bool = False):
        self.playwright = None
        self.api_client = ScraperAPI() if use_api else None

    async def search(self, query: str, filters: dict) -> List[JobListing]:
        # Implementation
        pass
```

**Anti-Detection Strategies**:
```python
# Playwright configuration
browser = await playwright.chromium.launch(
    headless=True,
    args=[
        '--disable-blink-features=AutomationControlled',
    ]
)

context = await browser.new_context(
    user_agent='Mozilla/5.0 ...',  # Realistic UA
    viewport={'width': 1920, 'height': 1080},
    locale='en-US',
)

# Random delays
await asyncio.sleep(random.uniform(2, 5))

# Rotate user agents
from fake_useragent import UserAgent
ua = UserAgent()
```

### 2. LinkedIn Enrichment Module

**Using Proxycurl**:
```python
import httpx

class LinkedInEnricher:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://nubela.co/proxycurl/api"
        self.client = httpx.AsyncClient()

    async def get_company_profile(self, linkedin_url: str) -> dict:
        """Cost: $0.01"""
        response = await self.client.get(
            f"{self.base_url}/linkedin/company",
            params={'url': linkedin_url},
            headers={'Authorization': f'Bearer {self.api_key}'}
        )
        return response.json()

    async def get_employees_in_taiwan(self, linkedin_url: str) -> List[dict]:
        """Cost: ~$0.03"""
        response = await self.client.get(
            f"{self.base_url}/linkedin/company/employees/",
            params={
                'url': linkedin_url,
                'country': 'Taiwan',
                'enrich_profiles': 'skip'  # Save costs
            },
            headers={'Authorization': f'Bearer {self.api_key}'}
        )
        return response.json()['employees']

    async def enrich_job(self, job: JobListing) -> EnrichedJob:
        # Find LinkedIn company URL (may need search)
        company_profile = await self.get_company_profile(job.linkedin_url)
        taiwan_employees = await self.get_employees_in_taiwan(job.linkedin_url)

        return EnrichedJob(
            **job.__dict__,
            company_size=company_profile['company_size'],
            industry=company_profile['industry'],
            taiwan_team_count=len(taiwan_employees),
            taiwan_team_members=taiwan_employees
        )
```

**Cost Optimization**:
```python
# Cache company data (same company, multiple jobs)
from functools import lru_cache
import hashlib

@lru_cache(maxsize=500)
async def get_company_cached(linkedin_url: str):
    return await get_company_profile(linkedin_url)

# Database caching
# Only re-enrich if > 7 days old
if company.enriched_at < datetime.now() - timedelta(days=7):
    await enrich_company(company)
```

### 3. Ranking System

**Multi-factor scoring**:
```python
from dataclasses import dataclass
from typing import List

@dataclass
class RankingConfig:
    target_industries: List[str]
    target_company_sizes: List[str]  # ['11-50', '51-200']
    min_taiwan_team: int = 1
    preferred_cities: List[str] = None  # ['Taipei', 'Hsinchu']

class JobRanker:
    def __init__(self, config: RankingConfig):
        self.config = config

    def calculate_score(self, job: EnrichedJob) -> float:
        score = 0.0

        # Critical: Taiwan team presence (0-50 points)
        score += min(job.taiwan_team_count * 10, 50)

        # Proximity bonus (0-20 points)
        if self.config.preferred_cities:
            city_matches = sum(
                1 for member in job.taiwan_team_members
                if member.city in self.config.preferred_cities
            )
            score += min(city_matches * 5, 20)

        # Industry match (0-15 points)
        if job.industry in self.config.target_industries:
            score += 15

        # Company size match (0-10 points)
        if job.company_size in self.config.target_company_sizes:
            score += 10

        # Freshness (0-5 points)
        days_old = (datetime.now() - job.posted_date).days
        score += max(0, 5 - (days_old / 7))

        return score

    def rank_jobs(self, jobs: List[EnrichedJob]) -> List[RankedJob]:
        ranked = [
            RankedJob(job=job, score=self.calculate_score(job))
            for job in jobs
            if job.taiwan_team_count >= self.config.min_taiwan_team
        ]
        return sorted(ranked, key=lambda x: x.score, reverse=True)
```

## Implementation Phases

### Phase 1: MVP (Week 1-2)
**Goal**: Basic working prototype

**Scope**:
- [ ] Single job board scraper (Indeed) using Playwright
- [ ] Basic job data storage (SQLite)
- [ ] Manual LinkedIn URL input (no automatic enrichment)
- [ ] Simple ranking by Taiwan team count
- [ ] Command-line interface

**Deliverables**:
```bash
python main.py search "senior software engineer" --remote --board indeed
# Output: 20 jobs ranked by Taiwan team presence
```

**Tech Stack**:
- Playwright
- SQLite
- Click (CLI)
- Pandas

### Phase 2: LinkedIn Integration (Week 3)
**Goal**: Automated enrichment

**Scope**:
- [ ] Proxycurl integration
- [ ] Automatic company LinkedIn URL discovery
- [ ] Employee location extraction
- [ ] Caching to minimize API costs

**Budget**: ~$20-40 for testing

### Phase 3: Multi-Board Support (Week 4)
**Goal**: Comprehensive job coverage

**Scope**:
- [ ] Add RemoteOK, We Work Remotely scrapers
- [ ] Job deduplication logic
- [ ] ScraperAPI integration for fallback

### Phase 4: Advanced Features (Week 5-6)
**Goal**: Production-ready system

**Scope**:
- [ ] PostgreSQL migration
- [ ] Advanced ranking algorithm
- [ ] Web UI (FastAPI + React) or dashboard
- [ ] Scheduled runs (daily job refresh)
- [ ] Email/Slack notifications for new high-ranking jobs
- [ ] Export to CSV/JSON

## Cost Analysis

### Monthly Operating Costs (for 1000 jobs/month)

| Component | Service | Cost |
|-----------|---------|------|
| Job Scraping (fallback) | ScraperAPI (1000 calls) | $49 |
| LinkedIn Enrichment | Proxycurl (1000 jobs × $0.04) | $40 |
| Infrastructure | Local/VPS | $0-10 |
| **Total** | | **$89-99/mo** |

### Cost Optimization Strategies

1. **Aggressive Caching**:
   - Cache company data for 30 days
   - Only enrich new companies
   - Reduces Proxycurl costs by ~70%

2. **Smart Scraping**:
   - Start with custom scrapers (free)
   - Only use ScraperAPI when blocked
   - Estimate: 20% usage = $10/mo instead of $49

3. **Targeted Searches**:
   - Focus on specific keywords/companies
   - Reduces total job volume
   - Process 200 jobs/month instead of 1000

**Optimized Monthly Cost**: **$15-25/mo**

## Development vs. Buy Decision Matrix

| Component | Build Custom | Buy API | Recommendation |
|-----------|--------------|---------|----------------|
| Job Board Scraping | Medium effort, full control | Easy, costly | **Hybrid**: Build + API fallback |
| LinkedIn Enrichment | High effort, risky | Easy, reliable | **Buy**: Use Proxycurl |
| Data Storage | Easy, full control | N/A | **Build**: PostgreSQL |
| Ranking | Easy, customizable | N/A | **Build**: Custom algorithm |
| Orchestration | Medium effort | N/A | **Build**: Celery/asyncio |

## Recommended Libraries & Tools

### Core Dependencies
```txt
# Web scraping
playwright==1.40.0
beautifulsoup4==4.12.2
httpx==0.25.2
parsel==1.8.1

# Anti-detection
fake-useragent==1.4.0

# Data processing
pandas==2.1.4
python-dateutil==2.8.2

# Database
sqlalchemy==2.0.23
alembic==1.13.0
psycopg2-binary==2.9.9  # PostgreSQL driver

# API integrations
proxycurl-py==0.1.0  # Proxycurl client

# Task queue (optional, for production)
celery==5.3.4
redis==5.0.1

# CLI
click==8.1.7
rich==13.7.0  # Beautiful terminal output

# Config management
pydantic==2.5.3
pydantic-settings==2.1.0
python-dotenv==1.0.0

# Logging & monitoring
loguru==0.7.2
sentry-sdk==1.38.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-playwright==0.4.3
```

## Security & Privacy Considerations

1. **Rate Limiting**: Implement exponential backoff
2. **robots.txt**: Respect crawl delays
3. **User Agents**: Rotate to appear as normal browser
4. **Data Storage**: Encrypt API keys, use environment variables
5. **Legal**: Review job board ToS, LinkedIn ToS
6. **GDPR**: If storing employee data, implement data retention policies

## Alternative Approaches Considered

### 1. Fully Custom Scraping (No Paid APIs)
**Pros**: Zero ongoing costs
**Cons**:
- High maintenance burden
- LinkedIn account ban risk
- Unreliable for production
**Verdict**: ❌ Not recommended

### 2. Fully API-Based (Bright Data/Oxylabs)
**Pros**: Zero maintenance, enterprise reliability
**Cons**:
- Very expensive ($600+/mo)
- Overkill for personal use
**Verdict**: ❌ Too expensive

### 3. Hybrid Approach (Recommended) ✅
**Pros**:
- Balanced cost/reliability
- Flexibility to optimize
- Scalable
**Cons**:
- Some maintenance required
**Verdict**: ✅ Best choice

## Success Metrics

1. **Coverage**: Successfully scrape 80%+ of target jobs
2. **Accuracy**: 95%+ correct company-job matching
3. **Taiwan Detection**: 90%+ accuracy in identifying Taiwan team members
4. **Cost**: Stay under $30/mo for 500 jobs
5. **Reliability**: 98%+ uptime for weekly searches

## Next Steps

1. **Review & Approve**: Review this specification
2. **Environment Setup**: Set up Python 3.10+ environment
3. **API Keys**: Register for Proxycurl (free tier to start)
4. **Phase 1 Development**: Start with MVP implementation
5. **Testing**: Test with 10-20 jobs before scaling

## Questions for Clarification

1. **Job Volume**: How many jobs do you expect to process weekly/monthly?
2. **Budget**: What's your comfortable monthly spend? ($10, $50, $100?)
3. **Target Industries**: Which specific industries are you targeting?
4. **Company Size**: Preferred team size ranges?
5. **Update Frequency**: How often do you want to run searches? (Daily, weekly?)
6. **Deployment**: Local laptop, or cloud VPS?

---

**Document Version**: 1.0
**Last Updated**: 2025-11-19
**Author**: Claude (Job Search Assistant Design)
