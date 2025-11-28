import asyncio
import os
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

async def test_proxy():
    print("Testing proxy config...")
    
    # Mock a proxy dict
    proxy_dict = {
        "server": "http://example.com:8080",
        "username": "user",
        "password": "pass"
    }
    
    try:
        config = BrowserConfig(
            browser_type="chromium",
            headless=True,
            proxy=proxy_dict # Try passing dict
        )
        print("BrowserConfig accepted dict!")
    except Exception as e:
        print(f"BrowserConfig rejected dict: {e}")

    # Try running with dict via proxy_config
    try:
        print("Running crawler with proxy_config...")
        config = BrowserConfig(
            browser_type="chromium",
            headless=True,
            proxy_config=proxy_dict # Use proxy_config
        )
        async with AsyncWebCrawler(config=config) as crawler:
            await crawler.arun("https://example.com")
        print("Crawler ran successfully with proxy_config!")
    except Exception as e:
        print(f"Crawler failed with proxy_config: {e}")

if __name__ == "__main__":
    asyncio.run(test_proxy())
