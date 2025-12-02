"""
Example configuration for IndeedCrawl4AIScraper with 6-Layer Anti-Detection Defense

This file demonstrates how to configure the enhanced Crawl4AI scraper to
circumvent Cloudflare Turnstile and other anti-bot measures.

IMPORTANT: For best results, use residential proxies, not datacenter proxies.
"""

import os
from src.scrapers.indeed_crawl4ai import IndeedCrawl4AIScraper

# ==============================================================================
# 6-Layer Anti-Detection Configuration
# ==============================================================================

# Basic Configuration (works without proxies, but lower success rate)
BASIC_CONFIG = {
    # Extraction
    'extraction_mode': 'css',  # Options: 'css', 'llm', 'hybrid'

    # Browser
    'browser': 'chromium',
    'headless': True,  # Set to False for debugging or manual captcha solving

    # Layer 4: Timing Configuration
    'min_page_delay': 15,  # Minimum seconds between pages
    'max_page_delay': 30,  # Maximum seconds between pages
    'cloudflare_backoff': 120,  # Wait time (seconds) after Cloudflare detection

    # Layer 6: Session Management
    'max_pages_per_session': 5,  # Recreate browser after N pages
}

# Advanced Configuration (recommended for production use)
ADVANCED_CONFIG = {
    # Extraction
    'extraction_mode': 'css',  # CSS is faster and cheaper than LLM

    # Browser
    'browser': 'chromium',
    'headless': True,

    # Layer 2: Proxy Rotation (CRITICAL for avoiding blocks)
    'proxy_list': [
        # Add your residential proxies here
        # Format: 'http://username:password@host:port'
        os.getenv('PROXY_1', 'http://user:pass@residential-proxy-1.example.com:8000'),
        os.getenv('PROXY_2', 'http://user:pass@residential-proxy-2.example.com:8000'),
        os.getenv('PROXY_3', 'http://user:pass@residential-proxy-3.example.com:8000'),
    ],
    'rotate_proxy_every': 2,  # Rotate proxy every N pages

    # Layer 4: Timing Configuration
    'min_page_delay': 15,  # Minimum seconds between pages (increase if still blocked)
    'max_page_delay': 30,  # Maximum seconds between pages
    'cloudflare_backoff': 120,  # Wait 2 minutes after Cloudflare detection

    # Layer 6: Session Management
    'max_pages_per_session': 5,  # Recreate browser session every 5 pages
}

# Conservative Configuration (slower but safest)
CONSERVATIVE_CONFIG = {
    # Extraction
    'extraction_mode': 'css',

    # Browser
    'browser': 'chromium',
    'headless': True,

    # Layer 2: Proxy Rotation
    'proxy_list': [
        # Use multiple residential proxies
        os.getenv('PROXY_1'),
        os.getenv('PROXY_2'),
        os.getenv('PROXY_3'),
        os.getenv('PROXY_4'),
        os.getenv('PROXY_5'),
    ],
    'rotate_proxy_every': 1,  # Rotate proxy EVERY page

    # Layer 4: Timing - Very conservative delays
    'min_page_delay': 25,  # 25-45 seconds between pages
    'max_page_delay': 45,
    'cloudflare_backoff': 180,  # Wait 3 minutes after Cloudflare

    # Layer 6: Session Management - Aggressive rotation
    'max_pages_per_session': 3,  # New session every 3 pages
}

# LLM-Based Extraction Configuration (more accurate but slower/costlier)
LLM_CONFIG = {
    # Extraction - requires OPENROUTER_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY
    'extraction_mode': 'hybrid',  # Try CSS first, fall back to LLM
    'llm_provider': 'openai/gpt-4o-mini',  # Or 'anthropic/claude-sonnet-4-20250514'

    # Browser
    'browser': 'chromium',
    'headless': True,

    # Layer 2: Proxy Rotation
    'proxy_list': [os.getenv('PROXY_1'), os.getenv('PROXY_2')],
    'rotate_proxy_every': 2,

    # Layer 4: Timing
    'min_page_delay': 20,
    'max_page_delay': 35,
    'cloudflare_backoff': 120,

    # Layer 6: Session Management
    'max_pages_per_session': 5,
}

# ==============================================================================
# Usage Examples
# ==============================================================================

async def example_basic_usage():
    """Basic usage without proxies (lower success rate)"""
    async with IndeedCrawl4AIScraper(config=BASIC_CONFIG) as scraper:
        jobs = await scraper.search(
            query="software engineer",
            location="Remote",
            max_results=50,
            remote_only=True
        )
        print(f"Found {len(jobs)} jobs")
        for job in jobs[:5]:
            print(f"- {job.title} at {job.company}")


async def example_production_usage():
    """Production usage with proxies and all defenses enabled"""
    async with IndeedCrawl4AIScraper(config=ADVANCED_CONFIG) as scraper:
        jobs = await scraper.search(
            query="product manager",
            location="San Francisco, CA",
            max_results=100,
            remote_only=False
        )
        print(f"Found {len(jobs)} jobs")
        return jobs


async def example_conservative_usage():
    """Very slow but safest approach - for when you're getting heavily blocked"""
    async with IndeedCrawl4AIScraper(config=CONSERVATIVE_CONFIG) as scraper:
        jobs = await scraper.search(
            query="data scientist",
            location="New York, NY",
            max_results=30,  # Limit results when using conservative settings
            remote_only=False
        )
        print(f"Found {len(jobs)} jobs")
        return jobs


# ==============================================================================
# Proxy Setup Guide
# ==============================================================================

"""
RESIDENTIAL PROXY PROVIDERS (Recommended):

1. Bright Data (formerly Luminati)
   - Most reliable, expensive
   - https://brightdata.com/
   - ~$500/month for 20GB

2. Smartproxy
   - Good balance of price/quality
   - https://smartproxy.com/
   - ~$75/month for 5GB

3. Oxylabs
   - High quality, expensive
   - https://oxylabs.io/
   - ~$300/month for 20GB

4. IPRoyal
   - Budget-friendly option
   - https://iproyal.com/
   - ~$50/month for 5GB

DATACENTER PROXIES (NOT Recommended):
- Cloudflare easily detects datacenter IPs
- Only use for testing, not production

FREE OPTIONS (Limited success):
- No proxy (direct connection) - works for ~1-2 pages
- Tor network - very slow, often blocked
- Public proxies - unreliable, likely blocked


PROXY CONFIGURATION:

Set environment variables:
    export PROXY_1="http://username:password@residential-1.example.com:8000"
    export PROXY_2="http://username:password@residential-2.example.com:8000"
    export PROXY_3="http://username:password@residential-3.example.com:8000"

Or pass directly in config:
    config = {
        'proxy_list': [
            'http://user:pass@host1:port',
            'http://user:pass@host2:port',
        ]
    }

SOCKS5 proxies are also supported:
    'socks5://user:pass@host:port'
"""

# ==============================================================================
# Troubleshooting
# ==============================================================================

"""
PROBLEM: Still getting blocked on page 2-3

SOLUTIONS:
1. Increase delays:
   'min_page_delay': 30,
   'max_page_delay': 60,

2. Rotate browser more frequently:
   'max_pages_per_session': 2,

3. Add more residential proxies:
   'proxy_list': [...5+ proxies...],
   'rotate_proxy_every': 1,

4. Use headful mode to see what's happening:
   'headless': False,


PROBLEM: Cloudflare challenges in headful mode

SOLUTIONS:
1. Wait 30-60 seconds for automatic solving
2. Manually solve the challenge when prompted
3. The scraper will continue after you solve it


PROBLEM: All proxies failing

SOLUTIONS:
1. Check proxy credentials are correct
2. Verify proxies are residential, not datacenter
3. Test proxies individually with curl:
   curl -x http://user:pass@proxy:port https://www.indeed.com

4. Contact proxy provider support


PROBLEM: Too slow / timing out

SOLUTIONS:
1. Reduce max_results (scrape fewer jobs)
2. Reduce delays (but increases block risk):
   'min_page_delay': 10,
   'max_page_delay': 15,

3. Use faster extraction:
   'extraction_mode': 'css',  # Not 'llm' or 'hybrid'

4. Increase page timeout in code if needed
"""

# ==============================================================================
# Main
# ==============================================================================

if __name__ == "__main__":
    import asyncio

    print("="*80)
    print("IndeedCrawl4AIScraper - Enhanced Configuration Example")
    print("="*80)
    print()
    print("This file demonstrates configuration options for the 6-layer anti-detection system:")
    print()
    print("Layer 1: Browser Fingerprint Randomization")
    print("  - Randomized User-Agents across browsers/OS")
    print("  - Randomized viewport sizes")
    print("  - Anti-detection browser flags")
    print()
    print("Layer 2: Proxy Rotation")
    print("  - Automatic proxy switching")
    print("  - Health tracking and failure handling")
    print("  - Round-robin with smart fallback")
    print()
    print("Layer 3: Human Behavior Simulation")
    print("  - Realistic mouse movements")
    print("  - Natural scrolling patterns")
    print("  - Reading pauses and hovers")
    print()
    print("Layer 4: Advanced Timing Strategy")
    print("  - Adaptive delays based on page number")
    print("  - Random 'think time' pauses")
    print("  - Exponential backoff on Cloudflare detection")
    print()
    print("Layer 5: Enhanced Cloudflare Detection")
    print("  - Multi-pattern detection")
    print("  - Automatic proxy rotation on detection")
    print("  - Intelligent retry logic")
    print()
    print("Layer 6: Session & Cookie Management")
    print("  - Periodic browser session rotation")
    print("  - Automatic cleanup after page limits")
    print("  - Fresh fingerprints on rotation")
    print()
    print("="*80)
    print()
    print("Example configurations available:")
    print("  - BASIC_CONFIG: No proxies, basic settings")
    print("  - ADVANCED_CONFIG: With proxies, recommended for production")
    print("  - CONSERVATIVE_CONFIG: Slowest but safest")
    print("  - LLM_CONFIG: Uses AI for extraction (more accurate)")
    print()
    print("To run an example:")
    print("  asyncio.run(example_production_usage())")
    print()
    print("="*80)
