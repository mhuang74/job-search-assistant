# Service Comparison & Quick Start Guide

## Job Board Scraping Services - Detailed Comparison

### Option 1: Custom Scraper with Playwright ⭐ (Recommended Primary)

**Cost**: Free (compute only)

**Pros**:
- Full control over scraping logic
- No per-request costs
- Can customize for any job board
- Learn once, scrape anywhere
- Best for development/testing

**Cons**:
- Requires maintenance when sites change
- Must handle CAPTCHAs yourself
- Need to implement anti-detection
- Rate limiting management

**Best For**:
- Initial development
- Low-volume usage (<100 jobs/day)
- Learning and experimentation
- Sites without aggressive blocking

**Implementation Complexity**: Medium

---

### Option 2: ScraperAPI ⭐ (Recommended Fallback)

**Website**: https://www.scraperapi.com/
**Cost**: $49/mo for 100K credits (1 request = 1-5 credits)

**Pricing Tiers**:
- Hobby: $49/mo - 100K credits
- Startup: $99/mo - 300K credits
- Business: $249/mo - 1M credits

**Pros**:
- Handles CAPTCHA automatically
- Rotating proxies included
- Works with ANY website (not just job boards)
- Geotargeting (search as if from Taiwan)
- JavaScript rendering
- Auto-retry on failures

**Cons**:
- Monthly subscription required
- Usage-based pricing
- Generic (not job-board optimized)

**Best For**:
- Fallback when custom scraper fails
- CAPTCHA-heavy sites
- Production reliability
- Multi-region scraping

**API Example**:
```python
import requests

payload = {
    'api_key': 'YOUR_API_KEY',
    'url': 'https://www.indeed.com/jobs?q=software+engineer&l=Remote',
    'render': 'true'  # Execute JavaScript
}
response = requests.get('http://api.scraperapi.com/', params=payload)
```

---

### Option 3: Decodo Indeed Scraper

**Website**: https://www.decodo.com/
**Cost**: ~$0.01-0.03 per job (pay-as-you-go)

**Pros**:
- Indeed-specific, structured data
- Pre-parsed results (no HTML parsing)
- Includes job details, company info
- No CAPTCHA handling needed
- Simple REST API

**Cons**:
- Only works for Indeed
- Per-job pricing can add up
- No control over scraping logic
- Dependent on their uptime

**Best For**:
- Indeed-only searches
- Structured data needs
- Quick MVP without scraping code

**API Example**:
```python
import requests

response = requests.get(
    'https://api.decodo.com/indeed/search',
    params={
        'api_key': 'YOUR_KEY',
        'q': 'software engineer',
        'l': 'Remote',
        'limit': 20
    }
)
jobs = response.json()['jobs']
```

**Cost Estimate**:
- 100 jobs: $1-3
- 1000 jobs: $10-30

---

### Option 4: Bright Data (formerly Luminati)

**Website**: https://brightdata.com/
**Cost**: Starting at $500/mo

**Pros**:
- Enterprise-grade reliability
- Job board specific APIs
- Massive proxy network
- Excellent documentation
- Dedicated account manager

**Cons**:
- Very expensive
- Overkill for personal projects
- Complex setup
- Minimum commitment

**Best For**:
- Enterprise applications
- High-volume scraping (>10K jobs/day)
- When cost is not a concern

**Verdict**: ❌ Too expensive for this use case

---

### Option 5: Oxylabs

**Website**: https://oxylabs.io/
**Cost**: Starting at $49/mo (limited), $600+/mo for full features

**Pros**:
- High success rates
- LinkedIn scraping support
- SERP scraping
- Good for job boards

**Cons**:
- Expensive for useful tiers
- Complex pricing
- Requires commitment

**Best For**:
- Commercial applications
- When LinkedIn scraping needed at scale

**Verdict**: ❌ Too expensive for personal use

---

### Option 6: SerpAPI

**Website**: https://serpapi.com/
**Cost**: $50/mo for 5K searches

**Pros**:
- Specialized in search engine scraping
- Indeed, LinkedIn Jobs integration
- Clean JSON results
- Good for meta-search

**Cons**:
- Limited to search results (not detail pages)
- Per-search pricing
- May miss job details

**Best For**:
- Job discovery phase
- Multi-board aggregation
- Quick searches

---

## LinkedIn Scraping Services Comparison

> **Important Update**: Proxycurl shut down in June 2025. The following are current alternatives as of November 2025.

### Option 1: Coresignal ⭐ (Recommended)

**Website**: https://coresignal.com/
**Cost**: Starting at $49/mo (credit-based pricing)

**Pricing**:
- Starter Plan: $49/mo with 250 API credits
- 14-day free trial with 200 credits (no credit card required)
- Self-service signup (no sales call needed)
- Custom pricing for higher volumes

**Data Coverage**:
- 694M+ employee records
- 92M+ company records
- 399M+ job posting records
- Data refreshed every 6 hours

**Pros**:
- Excellent price-to-value ratio
- Employee API with location filtering (Taiwan)
- Company API with industry, size, headquarters
- No LinkedIn account ban risk
- Reliable and regularly updated
- Free trial to test before committing
- Multiple data processing levels

**Cons**:
- Monthly subscription (not pure pay-per-use)
- Need to contact sales for pricing beyond starter tier
- Credit consumption varies by endpoint

**Best For**:
- Medium to high volume (200-1000 jobs/mo)
- Predictable monthly costs
- Production use

**Example**:
```python
import httpx

# Search for company
response = await httpx.post(
    'https://api.coresignal.com/cdapi/v1/professional_network/company/search/filter',
    headers={'Authorization': 'Bearer YOUR_API_KEY'},
    json={'name': 'Stripe', 'limit': 1}
)

# Get employees in Taiwan
response = await httpx.post(
    'https://api.coresignal.com/cdapi/v1/professional_network/employee/search/filter',
    headers={'Authorization': 'Bearer YOUR_API_KEY'},
    json={
        'company_id': company_id,
        'location': 'Taiwan',
        'limit': 100
    }
)
```

---

### Option 2: People Data Labs ⭐ (Good for Small Volume)

**Website**: https://www.peopledatalabs.com/
**Cost**: Free tier available, then pay-as-you-go

**Pricing**:
- Free: 100 person/company lookups per month
- Pro: $98/mo (350 person enrichments, 1K company lookups)
- Enterprise: Custom pricing (starts ~$2,500/mo)
- Per-record: Person $0.28, Company $0.10 (lower at scale)

**Data Coverage**:
- 1.5B+ person profiles
- Comprehensive company data
- Location-based filtering

**Pros**:
- Free tier perfect for testing
- Pay-per-use model (after free tier)
- Good for low volumes (<200 jobs/mo)
- Location-based employee search
- No LinkedIn account ban risk

**Cons**:
- Higher per-record costs than Coresignal
- Costs add up quickly at scale
- Better suited for smaller volumes

**Best For**:
- Small volume (<200 jobs/mo)
- Testing and MVP development
- Pay-per-use preference

**Example**:
```python
import httpx

# Enrich company
response = await httpx.get(
    'https://api.peopledatalabs.com/v5/company/enrich',
    params={
        'name': 'Stripe',
        'api_key': 'YOUR_API_KEY'
    }
)

# Search employees in Taiwan
response = await httpx.get(
    'https://api.peopledatalabs.com/v5/person/search',
    params={
        'query': {
            'location_country': 'Taiwan',
            'job_company_name': 'Stripe'
        },
        'size': 100,
        'api_key': 'YOUR_API_KEY'
    }
)
```

---

### Option 3: Fresh LinkedIn Scraper API (RapidAPI)

**Website**: https://rapidapi.com/freshdata-freshdata-default/api/fresh-linkedin-profile-data/
**Cost**: $200-500/mo for serious use

**Pricing**:
- Basic: Free (testing only)
- Ultra: $200/mo for 100K requests ($0.002/request)
- Mega: $500/mo for 500K requests ($0.001/request)

**Pros**:
- Very low cost per request
- High throughput (120-300 req/min)
- Best for high volume (>1000 jobs/mo)
- No LinkedIn account needed

**Cons**:
- High base cost ($200/mo minimum)
- Only cost-effective at high volume
- Need to manage RapidAPI integration

**Best For**:
- High volume (>1000 jobs/mo)
- When per-request cost matters more than base cost

---

### Option 4: PhantomBuster

**Website**: https://phantombuster.com/
**Cost**: $30-128/mo

**Pricing Tiers**:
- Starter: $30/mo - 20 hours automation
- Pro: $50/mo - 80 hours
- Team: $128/mo - 300 hours

**Pros**:
- Multi-purpose automation
- Chrome extension recorder
- LinkedIn + other platforms
- No-code options

**Cons**:
- Time-based pricing (confusing)
- Requires LinkedIn account (ban risk)
- Slower than APIs
- Monthly commitment

**Best For**:
- Multiple automation needs beyond LinkedIn
- When you need browser automation
- Sales/marketing teams

**Verdict**: 🤔 Not recommended - Coresignal and People Data Labs are better alternatives

---

### Option 5: Custom Selenium/Playwright Scraper

**Cost**: Free (risk of account ban)

**Pros**:
- No API costs
- Full control

**Cons**:
- LinkedIn actively blocks bots
- High risk of permanent ban
- Violates LinkedIn ToS
- CAPTCHA challenges
- Requires session management
- Frequent breakage

**Best For**:
- Not recommended

**Verdict**: ❌ Too risky, not worth it

---

### Option 6: Piloterr

**Website**: https://piloterr.com/
**Cost**: Starting at $99/mo

**Pros**:
- LinkedIn Profile & Company scrapers
- 50 free credits to test
- 60M+ companies in database

**Cons**:
- Uses browser automation (potential ban risk)
- More expensive than Coresignal starter
- Less data coverage than Coresignal

**Verdict**: 🤔 Coresignal and People Data Labs offer better value

---

## Recommended Stack Summary

### For Budget-Conscious / MVP (<$50/mo)

```
Job Scraping:
├── Primary: Custom Playwright scraper (FREE)
└── Fallback: ScraperAPI free tier or pay-per-use

LinkedIn:
└── People Data Labs free tier (100 lookups/mo) + pay-per-use

Storage:
└── SQLite (FREE)

Total: ~$0-20/mo
```

### For Medium Volume (<$100/mo)

```
Job Scraping:
├── Primary: Custom Playwright (FREE)
└── Fallback: ScraperAPI occasional use (~$10-20/mo)

LinkedIn:
└── Coresignal Starter ($49/mo for 250 credits)

Storage:
└── PostgreSQL on VPS (~$5-10/mo)

Total: ~$64-79/mo
```

### For High Volume / Production (<$200/mo)

```
Job Scraping:
├── Primary: Custom Playwright (FREE)
└── Fallback: ScraperAPI Hobby ($49/mo)

LinkedIn:
├── Coresignal custom plan ($99-149/mo) OR
└── Fresh LinkedIn API on RapidAPI ($200/mo)

Storage:
└── PostgreSQL on VPS (~$10/mo)

Total: ~$158-209/mo
```

---

## Quick Start: Implementation Path

### Week 1: Foundation (Local, Free)

**Goal**: Get first 10 jobs scraped and ranked

```bash
# 1. Setup
pip install playwright beautifulsoup4 pandas sqlalchemy click
playwright install chromium

# 2. Build basic Indeed scraper
# - Scrape 10 jobs
# - Store in SQLite
# - No LinkedIn yet (manual)

# 3. Simple ranking by company
# - User manually adds Taiwan team count
# - Rank by that number
```

**Cost**: $0

### Week 2: LinkedIn Integration

**Goal**: Auto-enrich 50 jobs

```bash
# 1. Sign up for People Data Labs or Coresignal
# - People Data Labs: 100 free lookups/mo
# - Coresignal: 14-day free trial (200 credits)

# 2. Build enrichment module
# - Search company by name
# - Get Taiwan employee count
# - Store in database

# 3. Test with 50 jobs
```

**Cost**: $0 (using free tiers)

### Week 3: Scale Up (Multi-Board)

**Goal**: 200+ jobs, multiple sources

```bash
# 1. Add RemoteOK scraper
# 2. Add We Work Remotely scraper
# 3. Implement deduplication
# 4. Enrich with People Data Labs or Coresignal
```

**Cost**: $0-49 (free tier or Coresignal starter)

### Week 4: Production Ready

**Goal**: Automated, scheduled, reliable

```bash
# 1. Add ScraperAPI fallback (optional)
# 2. Build scheduling (cron or Celery)
# 3. Add notifications (email/Slack)
# 4. Build simple web UI (optional)
```

**Cost**: ~$49-99/mo (Coresignal + optional ScraperAPI)

---

## API Key Setup Checklist

### Required for MVP
Choose ONE LinkedIn enrichment service:
- [ ] **Option A**: People Data Labs API key (https://www.peopledatalabs.com/)
  - Sign up for free tier (100 lookups/mo)
  - No credit card required for free tier

- [ ] **Option B**: Coresignal API key (https://coresignal.com/)
  - Sign up for 14-day free trial (200 credits)
  - Starter plan: $49/mo for production

### Optional (add later)
- [ ] ScraperAPI key (https://www.scraperapi.com/)
  - Free trial available
  - $49/mo Hobby plan for production

### Configuration (.env file)
```bash
# .env
# LinkedIn Enrichment (choose one)
PEOPLEDATALABS_API_KEY=your_key_here
# OR
CORESIGNAL_API_KEY=your_key_here

# Job Scraping (optional)
SCRAPERAPI_KEY=your_key_here  # optional

# Database
DATABASE_URL=sqlite:///jobs.db  # or postgresql://...

# LinkedIn
LINKEDIN_CACHE_DAYS=30

# Ranking
MIN_TAIWAN_TEAM_MEMBERS=1
TARGET_INDUSTRIES=Technology,SaaS,Fintech
TARGET_COMPANY_SIZES=11-50,51-200
```

---

## Cost Optimization Tips

### 1. Aggressive Caching
```python
# Only re-enrich company if >30 days old
if company.last_enriched < datetime.now() - timedelta(days=30):
    enrich(company)  # Costs API credits
else:
    use_cached_data(company)  # Free
```

**Savings**: 70-90% on LinkedIn costs

### 2. Batch Processing
```python
# Don't enrich immediately, batch daily
jobs = scrape_all_boards()  # Get 50 jobs
unique_companies = dedupe_companies(jobs)  # Only 20 unique
enrich_companies(unique_companies)  # 20 API calls

# vs enriching per job: 50 API calls
```

**Savings**: 60% on LinkedIn costs

### 3. Smart Filtering
```python
# Filter BEFORE enrichment
jobs = scrape_jobs()
filtered = [j for j in jobs if matches_criteria(j)]  # 50 -> 20
enrich(filtered)  # Only enrich relevant jobs
```

**Savings**: 60% on LinkedIn costs

### 4. Free Tier Stacking
- People Data Labs: 100 free lookups/month
- Coresignal: 14-day free trial (200 credits)
- ScraperAPI: 1000 free credits/month trial
- Use free tiers for testing

**Savings**: $0 for first 1-2 months

---

## Decision Tree: Which Services to Use?

```
START: How many jobs/month will you process?

├─ <200 jobs/month
│  ├─ Job Scraping: Playwright (free)
│  ├─ LinkedIn: People Data Labs free tier + pay-per-use
│  └─ Total: ~$0-20/mo ✅
│
├─ 200-500 jobs/month
│  ├─ Job Scraping: Playwright + ScraperAPI fallback (~$10-20/mo)
│  ├─ LinkedIn: Coresignal Starter ($49/mo)
│  └─ Total: ~$59-69/mo ✅
│
├─ 500-1000 jobs/month
│  ├─ Job Scraping: Playwright + ScraperAPI ($49/mo)
│  ├─ LinkedIn: Coresignal custom plan ($99-149/mo)
│  └─ Total: ~$148-198/mo 💰
│
└─ >1000 jobs/month
   ├─ Job Scraping: ScraperAPI ($99-249/mo)
   ├─ LinkedIn: Fresh LinkedIn API on RapidAPI ($200+/mo)
   └─ Total: ~$299-449/mo 💰💰

   Consider: Are you running a business?
   ├─ Yes: Worth the cost ✅
   └─ No: Reduce job volume to stay under $200/mo
```

---

## Testing Budget

### First Month (Testing Phase)
```
Option A - People Data Labs:
- Free tier: 100 lookups/month
- Test with 50 jobs (2 calls each = 100 credits)
- Cost: $0 ✅

Option B - Coresignal:
- 14-day free trial: 200 credits
- Test with 100 jobs (2 calls each = 200 credits)
- Cost: $0 ✅

ScraperAPI trial: $0
- 1000 free API calls
- Test fallback mechanism

Total: $0 ✅
```

### Second Month (Production)
```
Option A - People Data Labs:
- 100 free + pay-per-use
- 200 jobs × $0.38 = ~$38 (after free tier)

Option B - Coresignal:
- Starter plan: $49/mo (250 credits)
- Covers ~125 jobs/month

ScraperAPI: $0-49
- Use custom scraper mostly
- Only pay if needed

Total: $0-88
Average: ~$20-50
```

---

## Maintenance Expectations

### Custom Playwright Scrapers
- **Time**: 2-4 hours/month
- **Tasks**: Update selectors when sites change
- **Difficulty**: Easy-Medium

### API Integrations (Coresignal/PDL, ScraperAPI)
- **Time**: <1 hour/month
- **Tasks**: Monitor usage, adjust budgets
- **Difficulty**: Easy

### Database & Ranking
- **Time**: 1-2 hours/month
- **Tasks**: Optimize queries, tune ranking
- **Difficulty**: Easy

**Total Maintenance**: 4-7 hours/month

---

## Final Recommendation

For your use case (personal job search assistant, Taiwan team focus):

**Best Approach**:
```
✅ Custom Playwright scrapers (primary)
✅ ScraperAPI (fallback only, pay-as-needed)
✅ People Data Labs (LinkedIn enrichment - start with free tier)
   OR Coresignal (for higher volume, better value at $49/mo)
✅ PostgreSQL or SQLite (storage)
✅ Python with asyncio (orchestration)
```

**Expected Monthly Cost**:
- Development/Testing: $0 (using free tiers)
- Light Production (<200 jobs): $0-20
- Medium Production (200-500 jobs): $49-79
- Heavy Production (500-1000 jobs): $148-198

**Time to MVP**: 2-3 weeks

**Maintenance**: 4-7 hours/month

**Why this approach**:
- Start with free tiers (People Data Labs) to validate concept
- Scale to Coresignal when you need reliability and higher volume
- Custom Playwright gives you control and zero recurring costs for job scraping
- Can start at $0/month and scale predictably as your needs grow

This balances cost, reliability, and control perfectly for a personal project that could scale to commercial use.

---

**Questions?** Let me know if you need clarification on any service or want to adjust the recommendations based on your specific constraints.
