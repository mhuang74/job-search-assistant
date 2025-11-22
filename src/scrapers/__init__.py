"""Job board scrapers"""
from .base import BaseScraper
from .indeed import IndeedScraper  # SeleniumBase UC mode (default)

# Playwright-based scraper (optional, requires playwright package)
try:
    from .indeed_playwright import IndeedPlaywrightScraper
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    IndeedPlaywrightScraper = None
    PLAYWRIGHT_AVAILABLE = False

# Crawl4AI-based scraper (optional, requires crawl4ai package)
try:
    from .indeed_crawl4ai import IndeedCrawl4AIScraper
    CRAWL4AI_AVAILABLE = True
except ImportError:
    IndeedCrawl4AIScraper = None
    CRAWL4AI_AVAILABLE = False

__all__ = [
    'BaseScraper',
    'IndeedScraper',
    'IndeedPlaywrightScraper',
    'IndeedCrawl4AIScraper',
    'PLAYWRIGHT_AVAILABLE',
    'CRAWL4AI_AVAILABLE',
    'get_indeed_scraper'
]


def get_indeed_scraper(scraper_type: str = 'seleniumbase', config: dict = None):
    """
    Factory function to get the appropriate Indeed scraper

    Args:
        scraper_type: One of 'seleniumbase', 'playwright', or 'crawl4ai'
        config: Scraper configuration dict

    Returns:
        Instance of the selected scraper

    Available scrapers:
        - 'seleniumbase': SeleniumBase UC mode (default) - disconnects driver during page loads
        - 'playwright': Original Playwright implementation - basic anti-detection
        - 'crawl4ai': Crawl4AI-based scraper - advanced with LLM extraction options
    """
    scraper_type = scraper_type.lower()

    if scraper_type == 'crawl4ai':
        if not CRAWL4AI_AVAILABLE:
            raise ImportError(
                "Crawl4AI scraper requested but crawl4ai is not installed. "
                "Install with: pip install crawl4ai"
            )
        return IndeedCrawl4AIScraper(config)
    elif scraper_type == 'playwright':
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright scraper requested but playwright is not installed. "
                "Install with: pip install playwright && playwright install"
            )
        return IndeedPlaywrightScraper(config)
    elif scraper_type == 'seleniumbase':
        return IndeedScraper(config)
    else:
        raise ValueError(
            f"Unknown scraper type: {scraper_type}. "
            f"Choose from: 'seleniumbase', 'playwright', 'crawl4ai'"
        )
