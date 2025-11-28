"""Test Kameleo scraper without proxy"""
import asyncio
from src.scrapers.indeed_kameleo import IndeedKameleoScraper
from loguru import logger

async def test():
    # Explicitly no proxy
    config = {
        'kameleo_port': 5050,
        'proxy': None
    }

    logger.info("Testing without proxy...")
    async with IndeedKameleoScraper(config) as scraper:
        # Override to avoid environment proxy
        scraper.config['proxy'] = None

        jobs = await scraper.search(
            query='software engineer',
            location='Remote',
            max_results=5,
            remote_only=True
        )
        logger.info(f'Found {len(jobs)} jobs')
        for job in jobs[:3]:
            logger.info(f'  - {job.title} at {job.company}')

asyncio.run(test())
