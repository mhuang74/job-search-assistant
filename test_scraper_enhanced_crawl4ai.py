#!/usr/bin/env python3
"""
Test script for the enhanced IndeedCrawl4AIScraper with 6-Layer Anti-Detection

This script demonstrates how to use the enhanced scraper with different configurations.
"""

import asyncio
import os
from src.scrapers.indeed_crawl4ai import IndeedCrawl4AIScraper


async def test_basic_config():
    """Test with basic configuration (no proxies)"""
    print("="*80)
    print("TEST 1: Basic Configuration (No Proxies)")
    print("="*80)

    config = {
        'extraction_mode': 'css',
        'headless': True,
        'min_page_delay': 15,
        'max_page_delay': 30,
        'max_pages_per_session': 5,
    }

    print(f"\nConfiguration:")
    for key, value in config.items():
        print(f"  {key}: {value}")

    print(f"\nStarting scraper...")

    try:
        async with IndeedCrawl4AIScraper(config=config) as scraper:
            jobs = await scraper.search(
                query="software engineer",
                location="Remote",
                max_results=30,  # Small test
                remote_only=True
            )

            print(f"\n✅ SUCCESS: Found {len(jobs)} jobs")
            print(f"\nFirst 5 jobs:")
            for i, job in enumerate(jobs[:5], 1):
                print(f"  {i}. {job.title} at {job.company}")
                print(f"     Location: {job.location}")
                print(f"     URL: {job.url}")
                print()

            return jobs

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        raise


async def test_advanced_config():
    """Test with advanced configuration (with proxies)"""
    print("\n" + "="*80)
    print("TEST 2: Advanced Configuration (With Proxies)")
    print("="*80)

    # Check if proxies are configured
    proxy1 = os.getenv('PROXY_1')
    proxy2 = os.getenv('PROXY_2')
    proxy3 = os.getenv('PROXY_3')

    if not proxy1:
        print("\n⚠️  WARNING: No proxies configured!")
        print("Set PROXY_1, PROXY_2, PROXY_3 environment variables to test proxy rotation.")
        print("Example: export PROXY_1='http://user:pass@host:port'")
        print("\nSkipping proxy test...\n")
        return

    config = {
        'extraction_mode': 'css',
        'headless': False,
        'proxy_list': [proxy1, proxy2, proxy3],
        'rotate_proxy_every': 2,
        'min_page_delay': 15,
        'max_page_delay': 30,
        'max_pages_per_session': 5,
    }

    print(f"\nConfiguration:")
    for key, value in config.items():
        if key == 'proxy_list':
            print(f"  {key}: [{len([p for p in value if p])} proxies configured]")
        else:
            print(f"  {key}: {value}")

    print(f"\nStarting scraper with proxy rotation...")

    try:
        async with IndeedCrawl4AIScraper(config=config) as scraper:
            jobs = await scraper.search(
                query="product manager",
                location="San Francisco, CA",
                max_results=50,
                remote_only=False
            )

            print(f"\n✅ SUCCESS: Found {len(jobs)} jobs")
            print(f"\nFirst 5 jobs:")
            for i, job in enumerate(jobs[:5], 1):
                print(f"  {i}. {job.title} at {job.company}")
                print(f"     Location: {job.location}")
                print()

            return jobs

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        raise


async def test_conservative_config():
    """Test with conservative configuration (maximum safety)"""
    print("\n" + "="*80)
    print("TEST 3: Conservative Configuration (Maximum Safety)")
    print("="*80)

    config = {
        'extraction_mode': 'css',
        'headless': True,
        'rotate_proxy_every': 1,  # Rotate every page
        'min_page_delay': 25,
        'max_page_delay': 45,
        'cloudflare_backoff': 180,  # 3 minutes
        'max_pages_per_session': 3,  # Very aggressive rotation
    }

    print(f"\nConfiguration:")
    for key, value in config.items():
        print(f"  {key}: {value}")

    print(f"\n⚠️  This is VERY slow but safest configuration")
    print(f"Expected time for 20 jobs: ~15-20 minutes")

    print(f"\nStarting scraper...")

    try:
        async with IndeedCrawl4AIScraper(config=config) as scraper:
            jobs = await scraper.search(
                query="data scientist",
                location="New York, NY",
                max_results=20,  # Small test due to slow speed
                remote_only=False
            )

            print(f"\n✅ SUCCESS: Found {len(jobs)} jobs")
            print(f"\nFirst 5 jobs:")
            for i, job in enumerate(jobs[:5], 1):
                print(f"  {i}. {job.title} at {job.company}")
                print(f"     Location: {job.location}")
                print()

            return jobs

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        raise


async def main():
    """Run all tests"""
    print("\n" + "🛡️ " * 40)
    print("6-Layer Anti-Detection Defense System - Test Suite")
    print("🛡️ " * 40)

    print("\nThis will test the enhanced IndeedCrawl4AIScraper with:")
    print("  ✅ Layer 1: Browser Fingerprint Randomization")
    print("  ✅ Layer 2: Proxy Rotation Strategy")
    print("  ✅ Layer 3: Human Behavior Simulation")
    print("  ✅ Layer 4: Advanced Timing Strategy")
    print("  ✅ Layer 5: Enhanced Cloudflare Detection")
    print("  ✅ Layer 6: Session & Cookie Management")
    print()

    # Test 1: Basic config (always run)
    try:
        await test_basic_config()
    except Exception as e:
        print(f"\n❌ Test 1 failed: {e}")

    # Test 2: Advanced config (only if proxies configured)
    # try:
    #     await test_advanced_config()
    # except Exception as e:
    #     print(f"\n❌ Test 2 failed: {e}")

    # Test 3: Conservative config (optional - very slow)
    # try:
    #     await test_conservative_config()
    # except Exception as e:
    #     print(f"\n❌ Test 3 failed: {e}")

    print("\n" + "="*80)
    print("Test suite complete!")
    print("="*80)
    print("\nNext steps:")
    print("  1. Review the logs above for [AntiDetect] messages")
    print("  2. Check if Cloudflare was detected")
    print("  3. Configure proxies (PROXY_1, PROXY_2, PROXY_3) for better results")
    print("  4. Adjust delays if still getting blocked")
    print()
    print("For production use, see:")
    print("  - scraper_config_example.py (configuration examples)")
    print("  - ANTI_DETECTION_GUIDE.md (complete documentation)")
    print()


if __name__ == "__main__":
    asyncio.run(main())
