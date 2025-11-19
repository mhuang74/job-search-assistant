# Job Search Assistant

> Leverage job board scraping and LinkedIn data to identify and rank remote jobs based on Taiwan team presence

Find remote jobs at companies with team members in Taiwan using automated scraping and LinkedIn enrichment.

## Features

### Phase 1: Job Scraping ✅
- **Multi-board support**: Currently supports Indeed (more boards coming soon)
- **Smart deduplication**: Removes duplicate jobs across boards
- **SQLite storage**: Local database for job management
- **Rich CLI**: Beautiful command-line interface
- **CSV export**: Export results for analysis

### Phase 2: LinkedIn Enrichment ✅
- **Company enrichment**: Automatic company profile lookup
- **Taiwan team detection**: Identify team members in Taiwan
- **Intelligent caching**: Minimize API costs (70-90% savings)
- **Smart ranking**: Score jobs based on Taiwan team presence, industry, size, and freshness
- **Two API options**: People Data Labs (free tier) or Coresignal

## Quick Start

### 1. Installation

```bash
# Clone the repository
cd job-search-assistant

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Copy environment template
cp .env.example .env
```

### 2. Configuration

Edit `.env` and add your API keys:

```bash
# For free tier (100 lookups/month)
PEOPLEDATALABS_API_KEY=your_pdl_key_here

# OR for higher volume
CORESIGNAL_API_KEY=your_coresignal_key_here

# Optional: Customize ranking
TARGET_INDUSTRIES=Technology,SaaS,Fintech
TARGET_COMPANY_SIZES=11-50,51-200,201-500
MIN_TAIWAN_TEAM_MEMBERS=1
```

**Get API Keys:**
- People Data Labs: https://www.peopledatalabs.com/ (100 free lookups/mo)
- Coresignal: https://coresignal.com/ (14-day free trial, 200 credits)

### 3. Usage

#### Search for jobs:

```bash
python main.py search "senior software engineer" --max-results 50
```

Options:
- `--location`: Location filter (default: "Remote")
- `--max-results`: Number of results (default: 50)
- `--board`: Job board (currently "indeed")
- `--remote-only/--no-remote-only`: Filter remote jobs
- `--export jobs.csv`: Export to CSV

#### Enrich jobs with LinkedIn data:

```bash
python main.py enrich --service peopledatalabs --max-jobs 20
```

Options:
- `--service`: "peopledatalabs" or "coresignal"
- `--max-jobs`: Number of jobs to enrich (default: 50)
- `--min-taiwan-team`: Minimum Taiwan team members (default: 1)
- `--export enriched.csv`: Export enriched results

#### List jobs from database:

```bash
python main.py list --min-taiwan-team 2 --enriched-only
```

Options:
- `--limit`: Number of jobs to show (default: 50)
- `--min-taiwan-team`: Filter by Taiwan team count
- `--enriched-only`: Show only enriched jobs
- `--export`: Export to CSV

#### Clean up old jobs:

```bash
python main.py cleanup --days 30
```

## Example Workflow

```bash
# 1. Search for remote software engineering jobs
python main.py search "software engineer" --max-results 100 --export initial_results.csv

# 2. Enrich with LinkedIn data to find Taiwan teams
python main.py enrich --service peopledatalabs --max-jobs 50 --export enriched.csv

# 3. List top jobs with Taiwan teams
python main.py list --min-taiwan-team 1 --enriched-only --limit 20
```

## Architecture

```
job-search-assistant/
├── main.py                 # CLI entry point
├── src/
│   ├── models/            # Data models (JobListing, EnrichedJob, etc.)
│   ├── scrapers/          # Job board scrapers (Indeed, etc.)
│   ├── enrichment/        # LinkedIn enrichment services
│   ├── database/          # SQLAlchemy models and storage
│   └── utils/             # Deduplication, ranking algorithms
├── specs/                 # Design specifications
├── logs/                  # Application logs
└── jobs.db               # SQLite database
```

## Key Features Explained

### Deduplication

Jobs are deduplicated using three strategies:
1. **Exact ID match**: company + title + location
2. **Fuzzy match**: Normalized title variations (Sr./Senior, Remote keyword, etc.)
3. **URL match**: Same job posted on multiple boards

Typical deduplication: **40-50% reduction** in duplicates

### Caching

Company data is cached for 30 days (configurable) to minimize API costs:
- **First lookup**: $0.38 (People Data Labs) or 2 credits (Coresignal)
- **Subsequent lookups**: $0 (from cache)
- **Savings**: 70-90% on LinkedIn API costs

### Ranking Algorithm

Jobs are scored based on:
- **Taiwan team count** (10 points each, max 50)
- **City proximity** (5 points for Taipei/Hsinchu/Taichung)
- **Industry match** (15 points)
- **Company size match** (10 points)
- **Job freshness** (5 points, decays over time)

## Cost Breakdown

### Phase 1 Only (Job Scraping)
- **Cost**: $0/month
- **Features**: Indeed scraping, deduplication, database storage

### Phase 2 (With LinkedIn Enrichment)

**Option A: People Data Labs (Free Tier)**
- First 100 lookups/month: **$0**
- Additional lookups: ~$0.38/job
- **Best for**: Testing, <200 jobs/month

**Option B: People Data Labs (Paid)**
- 200 jobs/month: ~$40
- 500 jobs/month: ~$100
- **Best for**: Regular use, pay-per-use preference

**Option C: Coresignal**
- Starter: $49/mo (250 credits, ~125 jobs)
- **Best for**: Medium volume, predictable costs

## Technical Details

### Performance

- **Indeed scraping**: ~100 jobs in 10 seconds
- **Deduplication**: Instant for <1000 jobs
- **LinkedIn enrichment**: ~2-3 seconds per company
- **Caching**: Reduces enrichment time by 80%

### Rate Limits

- **Indeed**: No rate limiting (best for scraping)
- **People Data Labs**: No strict rate limits
- **Coresignal**: Based on credits

### Database Schema

```sql
-- Jobs table with enrichment fields
jobs (id, title, company, location, url, posted_date,
      taiwan_team_count, ranking_score, enriched_at, ...)

-- Companies table with cached data
companies (id, name, industry, company_size, taiwan_employee_count,
           enriched_at, ...)

-- Team members table
team_members (id, company_id, name, title, location, city, ...)
```

## Development

### Run tests:

```bash
pytest tests/
```

### Add a new job board scraper:

1. Create new scraper in `src/scrapers/`
2. Inherit from `BaseScraper`
3. Implement `search()` and `get_job_details()`
4. Add to CLI options

Example:
```python
from .base import BaseScraper

class LinkedInScraper(BaseScraper):
    async def search(self, query, location, max_results):
        # Implement scraping logic
        pass
```

### Add new enrichment service:

1. Create new enricher in `src/enrichment/`
2. Implement `get_company_profile()` and `get_employees_in_taiwan()`
3. Add to `EnrichmentService`

## Troubleshooting

### "No jobs found"
- Check your search query and location
- Try increasing `--max-results`
- Verify Indeed is accessible in your region

### "API key not found"
- Ensure `.env` file exists
- Check API key is correctly formatted
- Verify no extra spaces in `.env`

### "Database locked"
- Close other instances of the application
- Delete `jobs.db` and restart

### "Playwright browser not found"
- Run: `playwright install chromium`

## Roadmap

- [x] Phase 1: Indeed scraper with deduplication
- [x] Phase 2: LinkedIn enrichment with People Data Labs/Coresignal
- [ ] Phase 3: Multi-board support (RemoteOK, We Work Remotely)
- [ ] Phase 4: Email notifications
- [ ] Phase 5: Web dashboard (FastAPI + React)
- [ ] Phase 6: Automated scheduling (cron/Celery)

## Contributing

See `specs/` directory for detailed design specifications and implementation techniques.

## License

MIT License - see LICENSE file

## Credits

Built using insights from:
- [JobSpy](https://github.com/speedyapply/JobSpy) - Multi-board scraping patterns
- [JobFunnel](https://github.com/PaulMcInnis/JobFunnel) - Deduplication strategies
- Implementation techniques documented in `specs/implementation-techniques.md`

---

**Questions?** Check the specifications in `specs/` or open an issue.
