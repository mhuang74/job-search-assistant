"""Tests for Indeed Crawl4AI scraper"""
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Check if crawl4ai is available
try:
    from src.scrapers.indeed_crawl4ai import IndeedCrawl4AIScraper, CRAWL4AI_AVAILABLE
except ImportError:
    CRAWL4AI_AVAILABLE = False
    IndeedCrawl4AIScraper = None


@pytest.mark.skipif(not CRAWL4AI_AVAILABLE, reason="crawl4ai not installed")
class TestIndeedCrawl4AIScraper:
    """Test Crawl4AI-based Indeed scraper"""

    def test_init_default_config(self):
        """Test scraper initialization with default config"""
        scraper = IndeedCrawl4AIScraper()
        assert scraper.base_url == "https://www.indeed.com"
        assert scraper.extraction_mode == 'css'
        assert scraper.css_strategy is not None

    def test_init_custom_config(self):
        """Test scraper initialization with custom config"""
        config = {
            'extraction_mode': 'hybrid',
            'headless': False,
            'browser': 'firefox'
        }
        scraper = IndeedCrawl4AIScraper(config=config)
        assert scraper.extraction_mode == 'hybrid'
        assert scraper.config.get('headless') is False
        assert scraper.config.get('browser') == 'firefox'

    def test_build_search_url(self):
        """Test search URL construction"""
        scraper = IndeedCrawl4AIScraper()

        # Basic search
        url = scraper._build_search_url("software engineer", "Remote", 0, True)
        assert "q=software+engineer" in url or "q=software%20engineer" in url
        assert "l=Remote" in url
        assert "start=0" in url
        assert "sc=0kf" in url  # Remote filter

        # Page 2
        url = scraper._build_search_url("python developer", "New York", 1, False)
        assert "start=10" in url
        assert "sc=" not in url or "attr(DSQF7)" not in url  # No remote filter

    def test_parse_posted_date_just_posted(self):
        """Test date parsing for 'just posted'"""
        scraper = IndeedCrawl4AIScraper()

        result = scraper._parse_posted_date("Just posted")
        assert result.date() == datetime.now().date()

        result = scraper._parse_posted_date("PostedJust posted")
        assert result.date() == datetime.now().date()

    def test_parse_posted_date_days_ago(self):
        """Test date parsing for 'X days ago'"""
        scraper = IndeedCrawl4AIScraper()

        result = scraper._parse_posted_date("5 days ago")
        expected = datetime.now() - timedelta(days=5)
        assert result.date() == expected.date()

    def test_parse_posted_date_weeks_ago(self):
        """Test date parsing for 'X weeks ago'"""
        scraper = IndeedCrawl4AIScraper()

        result = scraper._parse_posted_date("2 weeks ago")
        expected = datetime.now() - timedelta(weeks=2)
        assert result.date() == expected.date()

    def test_parse_posted_date_empty(self):
        """Test date parsing for empty string"""
        scraper = IndeedCrawl4AIScraper()

        result = scraper._parse_posted_date("")
        assert result.date() == datetime.now().date()

    def test_parse_salary_range(self):
        """Test salary parsing for range format"""
        scraper = IndeedCrawl4AIScraper()

        # Annual range
        min_sal, max_sal = scraper._parse_salary({'salary': '$50,000 - $70,000 a year'})
        assert min_sal == 50000
        assert max_sal == 70000

        # Hourly range (should convert to annual)
        min_sal, max_sal = scraper._parse_salary({'salary': '$25 - $35 an hour'})
        assert min_sal == 25 * 2080  # 52000
        assert max_sal == 35 * 2080  # 72800

    def test_parse_salary_k_notation(self):
        """Test salary parsing for K notation"""
        scraper = IndeedCrawl4AIScraper()

        min_sal, max_sal = scraper._parse_salary({'salary': '$80K - $100K'})
        assert min_sal == 80000
        assert max_sal == 100000

    def test_parse_salary_pre_parsed(self):
        """Test salary when already parsed (from LLM extraction)"""
        scraper = IndeedCrawl4AIScraper()

        min_sal, max_sal = scraper._parse_salary({
            'salary_min': 60000,
            'salary_max': 80000
        })
        assert min_sal == 60000
        assert max_sal == 80000

    def test_parse_salary_empty(self):
        """Test salary parsing for empty input"""
        scraper = IndeedCrawl4AIScraper()

        min_sal, max_sal = scraper._parse_salary({})
        assert min_sal is None
        assert max_sal is None

    def test_item_to_job_listing(self):
        """Test conversion of extraction item to JobListing"""
        scraper = IndeedCrawl4AIScraper()

        item = {
            'title': 'Software Engineer',
            'company': 'Test Company',
            'location': 'Remote',
            'description': 'A great job opportunity',
            'job_key': 'abc123',
            'posted_date': '2 days ago',
            'salary': '$100,000 - $120,000 a year'
        }

        job = scraper._item_to_job_listing(item)

        assert job.title == 'Software Engineer'
        assert job.company == 'Test Company'
        assert job.location == 'Remote'
        assert job.description == 'A great job opportunity'
        assert job.url == 'https://www.indeed.com/viewjob?jk=abc123'
        assert job.salary_min == 100000
        assert job.salary_max == 120000
        assert job.remote_type == 'Remote'

    def test_item_to_job_listing_minimal(self):
        """Test conversion with minimal data"""
        scraper = IndeedCrawl4AIScraper()

        item = {
            'title': 'Developer',
            'company': '',
            'location': ''
        }

        job = scraper._item_to_job_listing(item)

        assert job.title == 'Developer'
        assert job.company == 'Unknown'
        assert job.location == 'Remote'

    def test_item_to_job_listing_no_title(self):
        """Test that items without title return None"""
        scraper = IndeedCrawl4AIScraper()

        item = {
            'title': '',
            'company': 'Test Company'
        }

        job = scraper._item_to_job_listing(item)
        assert job is None

    def test_parse_extraction_result_css(self):
        """Test parsing CSS extraction results"""
        scraper = IndeedCrawl4AIScraper()

        extracted = json.dumps([
            {
                'title': 'Job 1',
                'company': 'Company A',
                'location': 'Remote',
                'job_key': 'key1'
            },
            {
                'title': 'Job 2',
                'company': 'Company B',
                'location': 'New York',
                'job_key': 'key2'
            }
        ])

        jobs = scraper._parse_extraction_result(extracted, use_llm=False)

        assert len(jobs) == 2
        assert jobs[0].title == 'Job 1'
        assert jobs[1].title == 'Job 2'

    def test_parse_extraction_result_llm(self):
        """Test parsing LLM extraction results"""
        scraper = IndeedCrawl4AIScraper()

        extracted = json.dumps({
            'jobs': [
                {
                    'title': 'Senior Developer',
                    'company': 'Tech Corp',
                    'location': 'Remote',
                    'salary_min': 120000,
                    'salary_max': 150000,
                    'is_remote': True
                }
            ]
        })

        jobs = scraper._parse_extraction_result(extracted, use_llm=True)

        assert len(jobs) == 1
        assert jobs[0].title == 'Senior Developer'
        assert jobs[0].salary_min == 120000
        assert jobs[0].remote_type == 'Remote'

    def test_parse_extraction_result_empty(self):
        """Test parsing empty extraction results"""
        scraper = IndeedCrawl4AIScraper()

        jobs = scraper._parse_extraction_result("", use_llm=False)
        assert jobs == []

        jobs = scraper._parse_extraction_result(None, use_llm=False)
        assert jobs == []

    def test_parse_extraction_result_invalid_json(self):
        """Test parsing invalid JSON"""
        scraper = IndeedCrawl4AIScraper()

        jobs = scraper._parse_extraction_result("not valid json", use_llm=False)
        assert jobs == []

    def test_css_strategy_schema(self):
        """Test that CSS extraction schema is properly configured"""
        scraper = IndeedCrawl4AIScraper()

        schema = scraper._get_job_schema()

        assert schema['name'] == 'Indeed Jobs'
        assert 'baseSelector' in schema
        assert 'fields' in schema

        field_names = [f['name'] for f in schema['fields']]
        assert 'title' in field_names
        assert 'company' in field_names
        assert 'location' in field_names
        assert 'salary' in field_names
        assert 'job_key' in field_names


class TestCrawl4AIScraperFactory:
    """Test the scraper factory function"""

    def test_get_indeed_scraper_playwright(self):
        """Test getting Playwright scraper"""
        from src.scrapers import get_indeed_scraper, IndeedScraper

        scraper = get_indeed_scraper(use_crawl4ai=False)
        assert isinstance(scraper, IndeedScraper)

    @pytest.mark.skipif(not CRAWL4AI_AVAILABLE, reason="crawl4ai not installed")
    def test_get_indeed_scraper_crawl4ai(self):
        """Test getting Crawl4AI scraper"""
        from src.scrapers import get_indeed_scraper

        scraper = get_indeed_scraper(use_crawl4ai=True)
        assert isinstance(scraper, IndeedCrawl4AIScraper)

    def test_get_indeed_scraper_crawl4ai_not_installed(self):
        """Test error when crawl4ai requested but not installed"""
        from src.scrapers import get_indeed_scraper, CRAWL4AI_AVAILABLE

        if CRAWL4AI_AVAILABLE:
            pytest.skip("crawl4ai is installed, cannot test missing scenario")

        with pytest.raises(ImportError):
            get_indeed_scraper(use_crawl4ai=True)


class TestCrawl4AIScraperIntegration:
    """Integration tests (require network, use sparingly)"""

    @pytest.mark.skip(reason="Integration test - run manually")
    @pytest.mark.asyncio
    async def test_search_live(self):
        """Live integration test against Indeed"""
        scraper = IndeedCrawl4AIScraper(config={'headless': True})

        async with scraper:
            jobs = await scraper.search(
                query="python developer",
                location="Remote",
                max_results=5,
                remote_only=True
            )

        assert len(jobs) > 0
        assert all(job.title for job in jobs)
        assert all(job.company for job in jobs)
