"""Test script for IndeedKameleoScraper"""
import asyncio
import os
from src.scrapers.indeed_kameleo import IndeedKameleoScraper
from loguru import logger


async def test_search():
    """Test the Indeed Kameleo scraper"""

    # Optional: Configure proxy if needed
    config = {
        # Uncomment and configure if using a proxy
        # 'proxy': 'http://user:pass@proxy.example.com:8080',
        'kameleo_port': 5050,  # Default Kameleo port
    }

    # Load proxy from environment if available
    if os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY'):
        logger.info(f"Using proxy from environment: {os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')}")

    logger.info("Starting Indeed Kameleo scraper test...")
    logger.info("="*80)

    try:
        async with IndeedKameleoScraper(config) as scraper:
            # Search for jobs
            jobs = await scraper.search(
                query='technical product manager',
                location='Remote',
                max_results=20,
                remote_only=True
            )

            logger.info("\n" + "="*80)
            logger.info(f"RESULTS: Found {len(jobs)} jobs")
            logger.info("="*80)

            # Display results
            for idx, job in enumerate(jobs, 1):
                logger.info(f"\n{'─'*80}")
                logger.info(f"Job {idx}: {job.title}")
                logger.info(f"{'─'*80}")
                logger.info(f"  Company: {job.company}")
                logger.info(f"  Location: {job.location}")
                logger.info(f"  Posted: {job.posted_date.strftime('%Y-%m-%d')}")
                logger.info(f"  URL: {job.url}")
                if job.company_website:
                    logger.info(f"  Company Website: {job.company_website}")
                if job.description:
                    # Show first 200 chars of description
                    desc_preview = job.description[:200] + "..." if len(job.description) > 200 else job.description
                    logger.info(f"  Description: {desc_preview}")

            logger.info("\n" + "="*80)
            logger.info("✅ Test completed successfully!")
            logger.info("="*80)

            # Summary statistics
            jobs_with_websites = sum(1 for job in jobs if job.company_website)
            logger.info(f"\nStatistics:")
            logger.info(f"  Total jobs: {len(jobs)}")
            logger.info(f"  Jobs with company website: {jobs_with_websites} ({jobs_with_websites/len(jobs)*100:.1f}%)" if jobs else "  No jobs found")

    except Exception as e:
        logger.error(f"❌ Test failed with error: {type(e).__name__}: {e}")
        logger.exception("Full traceback:")
        raise


if __name__ == '__main__':
    # Configure logging for better output
    logger.add("test_kameleo_scraper.log", rotation="1 MB", level="DEBUG")

    asyncio.run(test_search())
