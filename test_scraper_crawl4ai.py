import asyncio
import os
from loguru import logger
from src.scrapers.indeed_crawl4ai import IndeedCrawl4AIScraper
from src.models import JobBoard

async def main():
    # Configure logger
    logger.add("scraper_verify.log", rotation="1 MB")

    print("Initializing IndeedCrawl4AIScraper...")
    scraper = IndeedCrawl4AIScraper(config={
        "headless": False,  # Run headful to see interaction
        "extraction_mode": "hybrid", # Use hybrid to enable LLM for company metadata
        "llm_provider": "openai/gpt-4o-mini"
    })

    async with scraper:
        print("Starting search...")
        jobs = await scraper.search(
            query="technical product manager",
            location="Remote",
            max_results=50
        )

        print(f"\nFound {len(jobs)} jobs:")
        for job in jobs:
            print(f"\nTitle: {job.title}")
            print(f"Company: {job.company}")
            print(f"Company Website: {job.company_website}")
            if hasattr(job, 'raw_html'): # Check if we can access the raw item or if we need to modify the model
                 pass 
            # We can't easily access the raw item here as it's converted to JobListing.
            # But I can check if I can add it to JobListing temporarily or just print it from the scraper logs.
            # Actually, I didn't add js_debug to JobListing model, so it won't be there.
            # I should have added it to the model or just relied on logs.
            # Let's check the logs.
            
            # Print debug HTML if available (we need to access it from logs or if we added it to model, but we didn't)
            # Since we can't easily access raw_html from JobListing, we rely on the logs.
            # However, I can try to access the raw item if I modify the scraper to return it, but I won't do that now.
            # I will just rely on the logs.


            
            if hasattr(job, 'company_size'):
                print(f"Company Size: {job.company_size}")
            if hasattr(job, 'industry'):
                print(f"Industry: {job.industry}")
            if hasattr(job, 'headquarters_location'):
                print(f"HQ: {job.headquarters_location}")

if __name__ == "__main__":
    # Ensure API key is present for LLM features
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("OPENROUTER_API_KEY"):
        print("WARNING: No OpenAI/OpenRouter API key found. LLM extraction might fail.")
    
    asyncio.run(main())
