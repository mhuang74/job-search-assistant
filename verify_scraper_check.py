import sys
import os
sys.path.append(os.getcwd())

try:
    from src.scrapers.indeed_crawl4ai import IndeedCrawl4AIScraper
    print("Successfully imported IndeedCrawl4AIScraper")
    
    scraper = IndeedCrawl4AIScraper(config={})
    print("Successfully initialized IndeedCrawl4AIScraper")
    
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
