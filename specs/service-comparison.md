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

### Option 1: Proxycurl ⭐ (Recommended)

**Website**: https://nubela.co/proxycurl
**Cost**: Pay-as-you-go, ~$0.01-0.05 per endpoint

**Pricing**:
- Company Profile: $0.01/call
- Employee Listing: $0.03/call
- Person Profile: $0.02/call

**Pros**:
- Most affordable LinkedIn API
- No monthly minimum
- Real-time data
- Reliable and fast
- Good documentation
- Filter employees by location

**Cons**:
- Costs add up at scale
- Need to find company LinkedIn URL first

**Best For**:
- Small to medium volume
- Pay-per-use model
- This exact use case

**Example**:
```python
import requests

# Get company profile
response = requests.get(
    'https://nubela.co/proxycurl/api/linkedin/company',
    params={'url': 'https://linkedin.com/company/stripe'},
    headers={'Authorization': 'Bearer YOUR_API_KEY'}
)

# Get employees in Taiwan
response = requests.get(
    'https://nubela.co/proxycurl/api/linkedin/company/employees/',
    params={
        'url': 'https://linkedin.com/company/stripe',
        'country': 'Taiwan',
        'enrich_profiles': 'skip'  # Save money
    },
    headers={'Authorization': 'Bearer YOUR_API_KEY'}
)
```

---

### Option 2: PhantomBuster

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

**Verdict**: 🤔 Good but Proxycurl is better for this use case

---

### Option 3: Custom Selenium/Playwright Scraper

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

### Option 4: Piloterr

**Website**: https://piloterr.com/
**Cost**: $19-99/mo

**Pros**:
- Affordable
- LinkedIn automation
- Browser-based

**Cons**:
- Uses your LinkedIn account (ban risk)
- Limited compared to Proxycurl
- Smaller community

**Verdict**: 🤔 Cheaper but riskier than Proxycurl

---

## Recommended Stack Summary

### For Budget-Conscious (<$25/mo)

```
Job Scraping:
├── Primary: Custom Playwright scraper (FREE)
└── Fallback: ScraperAPI free tier or pay-per-use

LinkedIn:
└── Proxycurl (pay-per-use, ~$8-15/mo for 200-400 enrichments)

Storage:
└── SQLite (FREE)

Total: ~$8-15/mo
```

### For Reliability-Focused (<$100/mo)

```
Job Scraping:
├── Primary: Custom Playwright (FREE)
└── Fallback: ScraperAPI Hobby ($49/mo)

LinkedIn:
└── Proxycurl (~$40/mo for 1000 enrichments)

Storage:
└── PostgreSQL on VPS (~$5-10/mo)

Total: ~$90-100/mo
```

### For MVP/Testing (<$10/mo)

```
Job Scraping:
└── Playwright only (FREE)

LinkedIn:
├── Manual lookup for testing
└── Proxycurl for 100-200 jobs (~$8/mo)

Storage:
└── SQLite (FREE)

Total: ~$0-8/mo
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

### Week 2: LinkedIn Integration (Proxycurl)

**Goal**: Auto-enrich 50 jobs

```bash
# 1. Sign up for Proxycurl
# - Free tier: $0 (100 free credits)
# - Or $10 prepaid

# 2. Build enrichment module
# - Find company LinkedIn URL
# - Get Taiwan employee count
# - Store in database

# 3. Test with 50 jobs
```

**Cost**: $0-2 (using free tier + minimal paid)

### Week 3: Scale Up (Multi-Board)

**Goal**: 200+ jobs, multiple sources

```bash
# 1. Add RemoteOK scraper
# 2. Add We Work Remotely scraper
# 3. Implement deduplication
# 4. Enrich all with Proxycurl
```

**Cost**: ~$8-12 (200 jobs × $0.04)

### Week 4: Production Ready

**Goal**: Automated, scheduled, reliable

```bash
# 1. Add ScraperAPI fallback (sign up for $49 plan)
# 2. Build scheduling (cron or Celery)
# 3. Add notifications (email/Slack)
# 4. Build simple web UI (optional)
```

**Cost**: ~$55-60/mo (ScraperAPI + Proxycurl)

---

## API Key Setup Checklist

### Required for MVP
- [ ] Proxycurl API key (https://nubela.co/proxycurl)
  - Sign up
  - Get free credits
  - Add payment method for pay-as-you-go

### Optional (add later)
- [ ] ScraperAPI key (https://www.scraperapi.com/)
  - Free trial available
  - $49/mo Hobby plan for production

### Configuration (.env file)
```bash
# .env
PROXYCURL_API_KEY=your_key_here
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
    enrich(company)  # Costs $0.04
else:
    use_cached_data(company)  # Free
```

**Savings**: 70-90% on LinkedIn costs

### 2. Batch Processing
```python
# Don't enrich immediately, batch daily
jobs = scrape_all_boards()  # Get 50 jobs
unique_companies = dedupe_companies(jobs)  # Only 20 unique
enrich_companies(unique_companies)  # 20 × $0.04 = $0.80

# vs enriching per job: 50 × $0.04 = $2.00
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
- Proxycurl: 100 free credits
- ScraperAPI: 1000 free credits/month trial
- Use free tiers for testing

**Savings**: $0 for first month

---

## Decision Tree: Which Services to Use?

```
START: How many jobs/month will you process?

├─ <100 jobs/month
│  ├─ Job Scraping: Playwright (free)
│  ├─ LinkedIn: Proxycurl pay-per-use (~$4/mo)
│  └─ Total: ~$4/mo ✅
│
├─ 100-500 jobs/month
│  ├─ Job Scraping: Playwright + ScraperAPI fallback ($49/mo)
│  ├─ LinkedIn: Proxycurl (~$20/mo)
│  └─ Total: ~$70/mo ✅
│
└─ >500 jobs/month
   ├─ Job Scraping: ScraperAPI ($99-249/mo)
   ├─ LinkedIn: Proxycurl (~$40+/mo)
   └─ Total: ~$140-290/mo 💰

   Consider: Are you running a business?
   ├─ Yes: Worth the cost ✅
   └─ No: Reduce job volume or find sponsors
```

---

## Testing Budget

### First Month (Testing Phase)
```
Proxycurl free tier: $0
- 100 free credits
- Test with 50 jobs (2 calls each = 100 credits)

ScraperAPI trial: $0
- 1000 free API calls
- Test fallback mechanism

Total: $0 ✅
```

### Second Month (Production)
```
Proxycurl: $8-15
- 200-400 enrichments
- 200 jobs × $0.04 = $8

ScraperAPI: $0-49
- Use custom scraper mostly
- Only pay if needed

Total: $8-64
Average: ~$30
```

---

## Maintenance Expectations

### Custom Playwright Scrapers
- **Time**: 2-4 hours/month
- **Tasks**: Update selectors when sites change
- **Difficulty**: Easy-Medium

### API Integrations (Proxycurl, ScraperAPI)
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
✅ Proxycurl (LinkedIn enrichment)
✅ PostgreSQL or SQLite (storage)
✅ Python with asyncio (orchestration)
```

**Expected Monthly Cost**:
- Development/Testing: $0-10
- Light Production (100 jobs): $10-20
- Heavy Production (500 jobs): $60-80

**Time to MVP**: 2-3 weeks

**Maintenance**: 4-7 hours/month

This balances cost, reliability, and control perfectly for a personal project that could scale to commercial use.

---

**Questions?** Let me know if you need clarification on any service or want to adjust the recommendations based on your specific constraints.
