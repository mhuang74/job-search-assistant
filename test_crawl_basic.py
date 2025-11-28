import asyncio
import os
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def test_crawl():
    print("Initializing crawler...")
    config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        verbose=True
    )
    
    async with AsyncWebCrawler(config=config) as crawler:
        print("Crawling example.com...")
        result = await crawler.arun(
            url="https://example.com",
            config=CrawlerRunConfig(
                bypass_cache=True
            )
        )
        
        if result.success:
            print("Success!")
            print(f"Content length: {len(result.markdown)}")
        else:
            print(f"Failed: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(test_crawl())
