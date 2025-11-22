"""Job board scrapers"""
from .base import BaseScraper
from .indeed import IndeedScraper

# Crawl4AI-based scraper (optional, requires crawl4ai package)
try:
    from .indeed_crawl4ai import IndeedCrawl4AIScraper
    CRAWL4AI_AVAILABLE = True
except ImportError:
    IndeedCrawl4AIScraper = None
    CRAWL4AI_AVAILABLE = False

__all__ = ['BaseScraper', 'IndeedScraper', 'IndeedCrawl4AIScraper', 'CRAWL4AI_AVAILABLE']


def get_indeed_scraper(use_crawl4ai: bool = False, config: dict = None):
    """
    Factory function to get the appropriate Indeed scraper

    Args:
        use_crawl4ai: If True, use Crawl4AI-based scraper (better anti-detection)
        config: Scraper configuration dict

    Returns:
        IndeedScraper or IndeedCrawl4AIScraper instance
    """
    if use_crawl4ai:
        if not CRAWL4AI_AVAILABLE:
            raise ImportError(
                "Crawl4AI scraper requested but crawl4ai is not installed. "
                "Install with: pip install crawl4ai"
            )
        return IndeedCrawl4AIScraper(config)
    return IndeedScraper(config)
