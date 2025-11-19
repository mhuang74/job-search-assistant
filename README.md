# Job Search Assistant

> Leverage job board scraping and LinkedIn data to identify and rank remote jobs based on Taiwan team presence

Find remote jobs at companies with team members in Taiwan using automated scraping and LinkedIn enrichment.

## 🚀 Status: Phases 1 & 2 Implemented

- ✅ **Phase 1**: Indeed job scraping with deduplication
- ✅ **Phase 2**: LinkedIn enrichment with People Data Labs/Coresignal integration
- 📋 **Phase 3**: Multi-board support (coming soon)

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Configure API keys
cp .env.example .env
# Edit .env and add your PEOPLEDATALABS_API_KEY or CORESIGNAL_API_KEY
```

### Usage Examples

```bash
# Search for jobs
python main.py search "senior software engineer" --max-results 50

# Enrich with LinkedIn data (requires API key)
python main.py enrich --service peopledatalabs --max-jobs 20

# List enriched jobs with Taiwan teams
python main.py list --min-taiwan-team 1 --enriched-only
```

## Features

### Phase 1: Job Scraping ✅
- Indeed scraper using Playwright
- Smart deduplication (3 strategies)
- SQLite database storage
- Rich CLI with tables
- CSV export

### Phase 2: LinkedIn Enrichment ✅
- Company profile enrichment
- Taiwan team member identification
- Intelligent caching (70-90% cost savings)
- Multi-factor ranking algorithm
- Support for People Data Labs & Coresignal APIs

## Documentation

See comprehensive documentation in `README_IMPLEMENTATION.md` and design specs in `specs/` directory:
- `specs/system-design.md` - Full architecture and tech stack
- `specs/service-comparison.md` - API service comparisons
- `specs/implementation-techniques.md` - Code patterns from open-source projects

## Cost

- **Phase 1 only**: $0/month
- **Phase 2 with free tier**: $0/month (100 jobs via People Data Labs)
- **Phase 2 production**: $49-79/month (200-500 jobs)
