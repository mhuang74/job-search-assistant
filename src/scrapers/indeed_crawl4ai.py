"""Indeed job board scraper using Crawl4AI for improved accuracy and anti-detection"""
from __future__ import annotations

import asyncio
import json
import os
import random
import re
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode, quote_plus, urlparse
from loguru import logger

from .base import BaseScraper
from ..models import JobListing, JobBoard, EnrichedJob

# Crawl4AI imports
try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
    from crawl4ai.extraction_strategy import JsonCssExtractionStrategy, LLMExtractionStrategy
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    logger.warning("crawl4ai not installed. Install with: pip install crawl4ai")


class ProxyRotator:
    """Rotate between multiple proxies with health tracking"""

    def __init__(self, proxy_list: List[str]):
        """
        Initialize proxy rotator

        Args:
            proxy_list: List of proxy URLs (e.g., ["http://user:pass@host:port", ...])
        """
        self.proxies = [p for p in proxy_list if p]  # Filter out None/empty
        self.current_idx = 0
        self.failures = {}  # Track failed proxies
        self.max_failures = 3

        if not self.proxies:
            logger.warning("[ProxyRotator] No proxies configured, will use direct connection")
        else:
            logger.info(f"[ProxyRotator] Initialized with {len(self.proxies)} proxies")

    def get_next_proxy(self) -> Optional[str]:
        """Get next working proxy with round-robin + health check"""
        if not self.proxies:
            return None

        # Try all proxies once
        for _ in range(len(self.proxies)):
            proxy = self.proxies[self.current_idx]
            self.current_idx = (self.current_idx + 1) % len(self.proxies)

            # Skip recently failed proxies
            if self.failures.get(proxy, 0) < self.max_failures:
                # Mask password in log
                safe_proxy = self._mask_password(proxy)
                logger.debug(f"[ProxyRotator] Selected proxy: {safe_proxy}")
                return proxy

        # All proxies failed, reset counters and try again
        logger.warning("[ProxyRotator] All proxies failed, resetting failure counters")
        self.failures.clear()
        return self.proxies[0] if self.proxies else None

    def mark_failure(self, proxy: str):
        """Mark a proxy as failed"""
        if proxy:
            self.failures[proxy] = self.failures.get(proxy, 0) + 1
            safe_proxy = self._mask_password(proxy)
            logger.warning(f"[ProxyRotator] Proxy failed ({self.failures[proxy]}/{self.max_failures}): {safe_proxy}")

    def mark_success(self, proxy: str):
        """Mark a proxy as successful (reset failure count)"""
        if proxy and proxy in self.failures:
            self.failures[proxy] = 0

    def _mask_password(self, proxy: str) -> str:
        """Mask password in proxy URL for safe logging"""
        if not proxy:
            return "None"
        try:
            parsed = urlparse(proxy)
            if parsed.password:
                return proxy.replace(parsed.password, "***")
            return proxy
        except:
            return "***"


class IndeedCrawl4AIScraper(BaseScraper):
    """Indeed scraper using Crawl4AI for enhanced reliability and accuracy"""

    def __init__(self, config: dict = None):
        super().__init__(JobBoard.INDEED, config)
        self.base_url = "https://www.indeed.com"
        self.crawler: Optional[AsyncWebCrawler] = None

        if not CRAWL4AI_AVAILABLE:
            raise ImportError("crawl4ai is required. Install with: pip install crawl4ai")

        # Extraction strategy configuration
        self.extraction_mode = self.config.get('extraction_mode', 'css')  # 'css', 'llm', or 'hybrid'
        self.llm_provider = self.config.get('llm_provider', 'openai/gpt-4o-mini')
        self.llm_model = self.config.get('llm_model')  # Optional: override default model

        # Initialize extraction strategies
        self.css_strategy = self._create_css_strategy()
        self.llm_strategy = None  # Lazy init when needed

        # Layer 2: Proxy Rotation
        proxy_list = self.config.get('proxy_list', [])
        if not proxy_list:
            # Check for PROXY_1 and PROXY_2 environment variables
            proxy_1 = os.getenv('PROXY_1')
            proxy_2 = os.getenv('PROXY_2')
            if proxy_1 or proxy_2:
                proxy_list = [p for p in [proxy_1, proxy_2] if p]
            else:
                # Fallback to single proxy from env or config
                single_proxy = self.config.get('proxy') or os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')
                if single_proxy:
                    proxy_list = [single_proxy]
        self.proxy_rotator = ProxyRotator(proxy_list)
        self.rotate_proxy_every = self.config.get('rotate_proxy_every', 2)  # Pages per proxy
        self.pages_since_proxy_rotation = 0
        self.current_proxy = None

        # Layer 4: Timing Configuration
        self.min_page_delay = self.config.get('min_page_delay', 15)
        self.max_page_delay = self.config.get('max_page_delay', 30)
        self.cloudflare_backoff = self.config.get('cloudflare_backoff', 120)
        self.cloudflare_detected_count = 0

        # Layer 6: Session Management
        self.session_id = str(uuid.uuid4())[:8]
        self.cookies_file = f"/tmp/indeed_cookies_{self.session_id}.json"
        self.max_pages_per_session = self.config.get('max_pages_per_session', 5)
        self.pages_scraped_in_session = 0

        logger.info(f"[Crawl4AI] Initialized scraper with session ID: {self.session_id}")
        logger.info(f"[Crawl4AI] Config: extraction_mode={self.extraction_mode}, "
                   f"rotate_proxy_every={self.rotate_proxy_every}, "
                   f"max_pages_per_session={self.max_pages_per_session}")

    def _create_css_strategy(self) -> JsonCssExtractionStrategy:
        """Create CSS-based extraction strategy for Indeed job cards"""
        schema = {
            "name": "Indeed Job Listings",
            "baseSelector": "div.job_seen_beacon, div[data-testid='job-card'], div.jobsearch-ResultsList > div",
            "fields": [
                {
                    "name": "title",
                    "selector": "h2.jobTitle a, h2.jobTitle span, a[data-jk]",
                    "type": "text"
                },
                {
                    "name": "company",
                    "selector": "span[data-testid='company-name'], span.companyName, div[data-testid='company-name']",
                    "type": "text"
                },
                {
                    "name": "location",
                    "selector": "div[data-testid='text-location'], div.companyLocation",
                    "type": "text"
                },
                {
                    "name": "salary",
                    "selector": "div[class*='salary-snippet'], div[class*='salaryOnly'], div.salary-snippet-container, div[data-testid='attribute_snippet_testid']",
                    "type": "text"
                },
                {
                    "name": "description",
                    "selector": "div.job-snippet, div[class*='job-snippet'], ul li, div[data-testid='jobsnippet_footer']",
                    "type": "text"
                },
                {
                    "name": "posted_date",
                    "selector": "span.date, span[class*='date'], span[data-testid='myJobsStateDate']",
                    "type": "text"
                },
                {
                    "name": "job_key",
                    "selector": "a[data-jk]",
                    "type": "attribute",
                    "attribute": "data-jk"
                },
                {
                    "name": "job_url",
                    "selector": "h2.jobTitle a, a[data-jk]",
                    "type": "attribute",
                    "attribute": "href"
                },
                {
                    "name": "company_url",
                    "selector": "a[href*='/cmp/']",
                    "type": "attribute",
                    "attribute": "href"
                },
                {
                    "name": "company_url_direct",
                    "selector": "div.job_seen_beacon, div[data-testid='job-card']",
                    "type": "attribute",
                    "attribute": "data-company-url"
                },
                {
                    "name": "js_debug",
                    "selector": "div.job_seen_beacon, div[data-testid='job-card']",
                    "type": "attribute",
                    "attribute": "data-js-debug"
                },
                {
                    "name": "js_status",
                    "selector": "div.job_seen_beacon, div[data-testid='job-card']",
                    "type": "attribute",
                    "attribute": "data-js-status"
                },
                {
                    "name": "js_test_body",
                    "selector": "body",
                    "type": "attribute",
                    "attribute": "data-js-test"
                },
                {
                    "name": "debug_html",
                    "selector": "div.job_seen_beacon, div[data-testid='job-card']",
                    "type": "attribute",
                    "attribute": "data-debug-html"
                }
            ]
        }
        return JsonCssExtractionStrategy(schema=schema)

    def _create_llm_strategy(self) -> Optional[LLMExtractionStrategy]:
        """Create LLM-based extraction strategy for enhanced accuracy"""
        # Check for API keys in priority order
        api_key = (
            os.getenv('OPENROUTER_API_KEY') or
            os.getenv('OPENAI_API_KEY') or
            os.getenv('ANTHROPIC_API_KEY')
        )

        if not api_key:
            logger.warning("No LLM API key found. Set OPENROUTER_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY for LLM extraction.")
            return None

        # Determine provider and model based on available key and config
        if self.llm_model:
            # Use explicitly configured model
            provider = self.llm_model
            logger.info(f"[Crawl4AI] Using configured LLM model: {provider}")
        elif os.getenv('OPENROUTER_API_KEY'):
            # Default to OpenAI GPT-4o Mini via OpenRouter
            provider = "openrouter/openai/gpt-4o-mini"
            logger.info("[Crawl4AI] Using OpenRouter with GPT-4o Mini model")
        elif os.getenv('ANTHROPIC_API_KEY'):
            provider = "anthropic/claude-sonnet-4-20250514"
            logger.info("[Crawl4AI] Using Anthropic Claude Sonnet 4")
        else:
            provider = self.llm_provider
            logger.info(f"[Crawl4AI] Using OpenAI model: {provider}")

        schema = {
            "type": "object",
            "properties": {
                "jobs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Job title"},
                            "company": {"type": "string", "description": "Company name"},
                            "location": {"type": "string", "description": "Job location"},
                            "salary_min": {"type": "integer", "description": "Minimum salary in USD (annual)"},
                            "salary_max": {"type": "integer", "description": "Maximum salary in USD (annual)"},
                            "salary_text": {"type": "string", "description": "Original salary text"},
                            "description": {"type": "string", "description": "Job description snippet"},
                            "posted_date": {"type": "string", "description": "When posted (e.g., '2 days ago')"},
                            "is_remote": {"type": "boolean", "description": "Whether remote position"},
                            "job_key": {"type": "string", "description": "Indeed job key from data-jk attribute"}
                        },
                        "required": ["title", "company"]
                    }
                }
            }
        }

        try:
            return LLMExtractionStrategy(
                provider=provider,
                api_token=api_key,
                schema=schema,
                extraction_type="schema",
                instruction="""
                Extract all job listings from this Indeed search results page.
                For salary, parse ranges like "$50,000 - $70,000 a year" into min/max integers.
                Convert hourly rates to annual (hourly * 2080).
                For is_remote, check if location contains "Remote" or has remote badge.
                Extract job_key from the data-jk attribute on job card links.
                """
            )
        except Exception as e:
            logger.warning(f"Failed to create LLM strategy: {e}")
            return None

    def _get_browser_config(self) -> BrowserConfig:
        """Configure browser with anti-detection settings (Layer 1: Fingerprint Randomization)"""

        # Layer 1: Randomize User-Agent across common browsers/OS
        user_agents = [
            # Chrome on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            # Safari on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
            # Chrome on Linux
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        ]

        # Layer 1: Randomize viewport from common resolutions
        viewports = [
            (1920, 1080),  # Full HD
            (1366, 768),   # HD
            (1536, 864),   # HD+
            (2560, 1440),  # 2K
            (1440, 900),   # MacBook Pro
        ]
        width, height = random.choice(viewports)

        # Add small random variations to viewport
        width += random.randint(-20, 20)
        height += random.randint(-20, 20)

        # Layer 2: Get proxy from rotator
        proxy_url = self.current_proxy or self.proxy_rotator.get_next_proxy()

        proxy_config = None
        if proxy_url:
            try:
                # Check if it's already a dict (passed from config)
                if isinstance(proxy_url, dict):
                    proxy_config = proxy_url
                else:
                    parsed = urlparse(proxy_url)
                    if parsed.hostname and parsed.port:
                        proxy_config = {'server': f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
                        if parsed.username:
                            proxy_config['username'] = parsed.username
                        if parsed.password:
                            proxy_config['password'] = parsed.password
                    else:
                        proxy_config = proxy_url
            except Exception as e:
                logger.warning(f"Failed to parse proxy URL: {e}")
                proxy_config = proxy_url

        # Determine if we should use proxy or proxy_config
        browser_config_args = {
            "browser_type": self.config.get('browser', 'chromium'),
            "headless": self.config.get('headless', True),
            "viewport_width": width,
            "viewport_height": height,
            "user_agent": random.choice(user_agents),
            "extra_args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
                "--no-sandbox",
            ]
        }

        if isinstance(proxy_config, dict):
            browser_config_args["proxy_config"] = proxy_config
        else:
            browser_config_args["proxy"] = proxy_config

        logger.debug(f"[Crawl4AI] Browser config: viewport={width}x{height}, headless={browser_config_args['headless']}")

        return BrowserConfig(**browser_config_args)

    def _get_crawler_config(self, use_llm: bool = False) -> CrawlerRunConfig:
        """Configure crawler run settings (Layer 3: Human Behavior Simulation)"""
        strategy = self.llm_strategy if use_llm and self.llm_strategy else self.css_strategy

        # Layer 3: Human behavior simulation JavaScript
        human_behavior_js = self._get_human_behavior_js()

        # Layer 6: Randomize delay
        delay = random.uniform(1.5, 3.0)

        return CrawlerRunConfig(
            extraction_strategy=strategy,
            # Anti-detection settings
            simulate_user=True,
            override_navigator=True,
            magic=True,
            # Content handling - wait for network to be idle (more realistic)
            wait_until="networkidle",
            # Wait for JS interaction to complete
            wait_for="body[data-interaction-done='true']",
            # Randomized delay
            delay_before_return_html=delay,
            # Caching - always bypass to avoid stale data
            cache_mode=CacheMode.BYPASS,
            # Session management - unique session per scraper instance
            session_id=f"indeed_{self.session_id}",
            # Layer 3: Human behavior simulation
            js_code=human_behavior_js,
        )

    def _get_human_behavior_js(self) -> str:
        """
        Layer 3: JavaScript to simulate realistic human behavior
        - Mouse movements
        - Scrolling patterns
        - Reading pauses
        - Random interactions
        """
        return """
        (async () => {
            try {
                console.log('[AntiDetect] Starting human behavior simulation...');

                // Helper: Sleep function
                const sleep = (ms) => new Promise(r => setTimeout(r, ms));

                // Helper: Random number in range
                const rand = (min, max) => Math.random() * (max - min) + min;

                // 1. Simulate mouse movements
                function simulateMouseMove() {
                    const event = new MouseEvent('mousemove', {
                        view: window,
                        bubbles: true,
                        cancelable: true,
                        clientX: rand(100, window.innerWidth - 100),
                        clientY: rand(100, window.innerHeight - 100)
                    });
                    document.dispatchEvent(event);
                }

                // 2. Simulate realistic scrolling (like a human reading)
                async function humanScroll() {
                    const scrollHeight = document.documentElement.scrollHeight;
                    const viewportHeight = window.innerHeight;
                    const scrollSteps = 4 + Math.floor(rand(0, 4)); // 4-7 steps

                    console.log(`[AntiDetect] Scrolling in ${scrollSteps} steps`);

                    for (let i = 0; i < scrollSteps; i++) {
                        // Calculate scroll position with some randomness
                        const progress = (i + 1) / scrollSteps;
                        const targetScroll = (scrollHeight - viewportHeight) * progress;
                        const randomOffset = rand(-50, 50);

                        window.scrollTo({
                            top: Math.max(0, targetScroll + randomOffset),
                            behavior: 'smooth'
                        });

                        // Random mouse movements during scroll
                        for (let j = 0; j < 3; j++) {
                            await sleep(rand(100, 300));
                            simulateMouseMove();
                        }

                        // Pause to "read" (longer pauses in middle of page)
                        const readTime = i === 0 || i === scrollSteps - 1 ?
                            rand(500, 1000) : rand(800, 1500);
                        await sleep(readTime);
                    }

                    // Scroll back up a bit (humans often do this)
                    if (Math.random() < 0.3) {
                        await sleep(rand(300, 600));
                        window.scrollTo({
                            top: rand(0, 300),
                            behavior: 'smooth'
                        });
                    }
                }

                // 3. Simulate hover over random elements
                async function simulateHovers() {
                    const hoverableSelectors = [
                        '.job_seen_beacon',
                        'h2.jobTitle',
                        '.companyName',
                        'div[data-testid="job-card"]'
                    ];

                    for (const selector of hoverableSelectors) {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length > 0) {
                            const randomElement = elements[Math.floor(rand(0, elements.length))];
                            if (randomElement) {
                                const rect = randomElement.getBoundingClientRect();
                                const event = new MouseEvent('mouseover', {
                                    view: window,
                                    bubbles: true,
                                    cancelable: true,
                                    clientX: rect.left + rect.width / 2,
                                    clientY: rect.top + rect.height / 2
                                });
                                randomElement.dispatchEvent(event);
                                await sleep(rand(200, 500));
                                break;
                            }
                        }
                    }
                }

                // Execute behavior sequence
                // Initial delay (page load time)
                await sleep(rand(800, 1500));

                // Random mouse movements
                for (let i = 0; i < 3; i++) {
                    simulateMouseMove();
                    await sleep(rand(100, 300));
                }

                // Scroll through page
                await humanScroll();

                // Hover over some elements
                await simulateHovers();

                // Final mouse movements
                for (let i = 0; i < 2; i++) {
                    simulateMouseMove();
                    await sleep(rand(100, 200));
                }

                // Small final pause
                await sleep(rand(500, 1000));

                console.log('[AntiDetect] Human behavior simulation complete');
                document.body.setAttribute('data-interaction-done', 'true');

            } catch (e) {
                console.error('[AntiDetect] Error in behavior simulation:', e);
                // Still mark as done so scraper doesn't hang
                document.body.setAttribute('data-interaction-done', 'true');
            }
        })();
        """

    def _get_interaction_js(self) -> str:
        """
        JavaScript to click job cards and extract company profile URLs from the details panel.
        Injects the found URL into the job card's DOM as 'data-company-url'.
        """
        return """
        (async () => {
            try {
                console.log("[JS] Starting job card interaction sequence...");
                document.body.setAttribute('data-js-test', 'started');
                
                // Wait for jobs to render
                await new Promise(r => setTimeout(r, 3000));
                
                const jobs = document.querySelectorAll('div.job_seen_beacon, div[data-testid="job-card"], div.jobsearch-ResultsList > div');
                console.log("[JS] Found " + jobs.length + " jobs");
                
                if (jobs.length === 0) {
                    document.body.setAttribute('data-js-status', 'no-jobs-found');
                }
                
                for (const job of jobs) {
                    job.setAttribute('data-js-debug', 'ran');
                    // Find the clickable title/link
                    const titleLink = job.querySelector('h2.jobTitle a, a[data-jk], a.jcs-JobTitle');
                    
                    if (titleLink) {
                    // Debug: Modify title to prove we touched it
                    titleLink.innerText = titleLink.innerText + " [JS]";
                    
                    // Scroll into view to ensure clickability
                        titleLink.scrollIntoView({behavior: 'smooth', block: 'center'});
                        await new Promise(r => setTimeout(r, 500));
                        
                        console.log("[JS] Clicking job:", titleLink.innerText);
                        titleLink.click();
                        
                        // Wait for details panel to load/update
                        // We look for the right pane container
                        await new Promise(r => setTimeout(r, 2000));
                        
                        // Try to find company link in the right pane
                    // Selectors based on common Indeed layouts
                    const rightPane = document.querySelector('.jobsearch-RightPane, #vjs-container');
                    if (rightPane) {
                        const companyLink = rightPane.querySelector(
                            'div[data-testid="company-name"] a, ' +
                            'a[href*="/cmp/"], ' +
                            'div[data-testid="jobsearch-CompanyProfileLink"] a, ' +
                            '.jobsearch-CompanyInfoContainer a, ' +
                            '.jobsearch-JobInfoHeader-companyName a'
                        );
                        
                        if (companyLink) {
                            console.log("[JS] Found company URL:", companyLink.href);
                            job.setAttribute('data-company-url', companyLink.href);
                        } else {
                            console.log("[JS] No company link found in right pane");
                            job.setAttribute('data-js-status', 'no-company-link');
                            
                            // Debug: Capture HTML of company info area
                            const companyInfo = rightPane.querySelector('.jobsearch-CompanyInfoContainer, .jobsearch-JobInfoHeader-companyName, div[data-testid="company-name"]');
                            if (companyInfo) {
                                job.setAttribute('data-debug-html', companyInfo.innerHTML.substring(0, 1000));
                            } else {
                                job.setAttribute('data-debug-html', 'No company info container found');
                            }
                        }
                    } else {
                        console.log("[JS] Right pane not found");
                        job.setAttribute('data-js-status', 'no-right-pane');
                    }
                } else {
                     job.setAttribute('data-js-status', 'no-title-link');
                }
                }
                console.log("[JS] Interaction sequence complete.");
                document.body.setAttribute('data-interaction-done', 'true');
            } catch (e) {
                console.error("[JS] Error:", e);
                document.body.setAttribute('data-js-error', e.message);
                // Ensure we still mark as done so scraper doesn't hang forever
                document.body.setAttribute('data-interaction-done', 'true');
            }
        })();
        """

    async def _smart_delay(self, page_num: int, cloudflare_detected: bool = False):
        """
        Layer 4: Implement human-like, adaptive delays between page requests

        Args:
            page_num: Current page number (0-indexed)
            cloudflare_detected: Whether Cloudflare challenge was detected
        """
        if cloudflare_detected:
            # If we hit Cloudflare, back off significantly
            delay = random.uniform(self.cloudflare_backoff * 0.8, self.cloudflare_backoff * 1.2)
            logger.warning(f"[AntiDetect] Cloudflare detected, backing off for {delay:.1f}s")
            self.cloudflare_detected_count += 1
        elif page_num == 0:
            # First page - shorter delay (just started browsing)
            delay = random.uniform(2, 5)
        elif page_num < 3:
            # Early pages - moderate delay
            delay = random.uniform(self.min_page_delay * 0.5, self.min_page_delay)
        else:
            # Later pages - longer delays (Cloudflare gets more suspicious)
            delay = random.uniform(self.min_page_delay, self.max_page_delay)

            # Add random "think time" occasionally (20% chance)
            # Simulates user pausing to think/do something else
            if random.random() < 0.2:
                think_time = random.uniform(5, 15)
                logger.info(f"[AntiDetect] Adding 'human think time': {think_time:.1f}s")
                delay += think_time

        logger.debug(f"[AntiDetect] Waiting {delay:.1f}s before next action...")
        await asyncio.sleep(delay)

    async def _should_rotate_browser(self) -> bool:
        """
        Layer 6: Determine if we should recreate browser session

        Returns:
            True if browser should be recreated
        """
        # Rotate if we've hit session limit
        if self.pages_scraped_in_session >= self.max_pages_per_session:
            logger.info(f"[AntiDetect] Reached session limit ({self.max_pages_per_session} pages), rotating browser...")
            return True

        # Rotate if Cloudflare has been detected multiple times
        if self.cloudflare_detected_count >= 2:
            logger.warning(f"[AntiDetect] Cloudflare detected {self.cloudflare_detected_count} times, rotating browser...")
            return True

        return False

    async def _rotate_browser(self):
        """
        Layer 1 & 2: Recreate browser with new fingerprint and proxy

        This helps avoid accumulated fingerprinting signals
        """
        logger.info("[AntiDetect] Rotating browser session...")

        # Close current browser
        if self.crawler:
            await self.crawler.__aexit__(None, None, None)
            self.crawler = None

        # Reset counters
        self.pages_scraped_in_session = 0
        self.cloudflare_detected_count = 0

        # Rotate proxy
        self.current_proxy = self.proxy_rotator.get_next_proxy()
        self.pages_since_proxy_rotation = 0

        # Wait a bit before recreating (simulate closing/reopening browser)
        await asyncio.sleep(random.uniform(3, 8))

        # Reinitialize browser with new config (new user-agent, viewport, etc.)
        self.crawler = AsyncWebCrawler(config=self._get_browser_config())
        await self.crawler.__aenter__()

        logger.info("[AntiDetect] Browser rotation complete")

    async def __aenter__(self):
        """Initialize crawler context"""
        self.crawler = AsyncWebCrawler(config=self._get_browser_config())
        await self.crawler.__aenter__()
        logger.info("[Crawl4AI] Browser initialized with 6-layer anti-detection defense")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup crawler context"""
        if self.crawler:
            await self.crawler.__aexit__(exc_type, exc_val, exc_tb)
            self.crawler = None
            logger.info("[Crawl4AI] Browser closed")

    async def search(
        self,
        query: str,
        location: str = "Remote",
        max_results: int = 50,
        remote_only: bool = True
    ) -> List[JobListing]:
        """
        Search for jobs on Indeed using Crawl4AI

        Args:
            query: Job search query (e.g., "software engineer")
            location: Location filter (default: "Remote")
            max_results: Maximum number of results to return
            remote_only: Filter for remote jobs only

        Returns:
            List of JobListing objects
        """
        logger.info(f"[Crawl4AI] Searching Indeed: query='{query}', location='{location}', max_results={max_results}")

        # Initialize LLM strategy if needed
        if self.extraction_mode in ('llm', 'hybrid') and not self.llm_strategy:
            self.llm_strategy = self._create_llm_strategy()

        jobs = []
        page_num = 0
        max_pages = min((max_results // 15) + 1, 10)  # Indeed shows ~15 jobs per page
        consecutive_failures = 0
        max_consecutive_failures = 3

        while len(jobs) < max_results and page_num < max_pages:
            # Layer 6: Check if we should rotate browser session
            if await self._should_rotate_browser():
                await self._rotate_browser()

            # Layer 2: Check if we should rotate proxy
            if self.pages_since_proxy_rotation >= self.rotate_proxy_every:
                old_proxy = self.current_proxy
                self.current_proxy = self.proxy_rotator.get_next_proxy()
                if old_proxy != self.current_proxy:
                    logger.info(f"[AntiDetect] Rotating proxy after {self.pages_since_proxy_rotation} pages")
                    # Need to recreate browser with new proxy
                    await self._rotate_browser()
                self.pages_since_proxy_rotation = 0

            url = self._build_search_url(query, location, page_num, remote_only)
            logger.info(f"[Crawl4AI] Scraping page {page_num + 1}/{max_pages}: {url}")

            # Retry logic for page navigation
            max_retries = 3
            retry_count = 0
            page_success = False
            cloudflare_detected_this_page = False

            while retry_count < max_retries:
                try:
                    # Determine extraction strategy for this page
                    use_llm = self.extraction_mode == 'llm'
                    
                    # Add stealth headers
                    headers = {
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Cache-Control': 'max-age=0',
                    }

                    # Update crawler config with headers if possible, or just rely on browser config
                    # Crawl4AI's run config doesn't directly take headers in all versions, 
                    # but we can try to pass them if supported or rely on the browser context.
                    # For now, we'll rely on the browser config we set up, but we can add extra args if needed.
                    
                    result = await self.crawler.arun(
                        url=url,
                        config=self._get_crawler_config(use_llm=use_llm)
                    )

                    # Layer 5: Enhanced Cloudflare Detection
                    if result.html and ("challenges.cloudflare.com" in result.html or
                                       "Verify you are human" in result.html or
                                       "Just a moment" in result.html or
                                       "cf-challenge" in result.html):
                        cloudflare_detected_this_page = True
                        logger.warning(f"[Crawl4AI] ⚠️  Cloudflare Turnstile challenge detected on page {page_num + 1}!")

                        # Mark current proxy as potentially problematic
                        if self.current_proxy:
                            self.proxy_rotator.mark_failure(self.current_proxy)

                        if not self.config.get('headless', True):
                            logger.warning("[Crawl4AI] Headful mode detected. Waiting 30s for manual solution...")
                            await asyncio.sleep(30)
                            # Retry immediately after wait
                            continue
                        else:
                            logger.error("[Crawl4AI] Cloudflare challenge in headless mode.")
                            logger.error("[Crawl4AI] Skipping this page - will rotate browser/proxy and try next page.")
                            # Force browser rotation on next iteration
                            self.cloudflare_detected_count += 1
                            consecutive_failures += 1

                            # Skip this page by incrementing page_num before breaking
                            page_num += 1

                            # Apply Cloudflare backoff delay before continuing
                            await self._smart_delay(page_num, cloudflare_detected=True)

                            # Break out of retry loop - no point retrying Cloudflare
                            break

                    if not result.success:
                        logger.warning(f"[Crawl4AI] Failed to fetch page: {result.error_message}")
                        # Check for specific navigation errors
                        if "navigation" in str(result.error_message).lower() or "timeout" in str(result.error_message).lower():
                             raise RuntimeError(f"Navigation failed: {result.error_message}")
                        
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            logger.error(f"[Crawl4AI] {max_consecutive_failures} consecutive failures, stopping")
                            return jobs[:max_results]
                        
                        await asyncio.sleep(5)  # Wait before retry
                        retry_count += 1
                        continue

                    consecutive_failures = 0  # Reset on success
                    page_success = True

                    # Parse extraction results
                    page_jobs = self._parse_extraction_result(result.extracted_content, use_llm)

                    # Hybrid mode: retry with LLM if CSS extraction failed
                    if self.extraction_mode == 'hybrid' and not page_jobs and self.llm_strategy:
                        logger.info("[Crawl4AI] CSS extraction failed, trying LLM extraction...")
                        result = await self.crawler.arun(
                            url=url,
                            config=self._get_crawler_config(use_llm=True)
                        )
                        if result.success:
                            page_jobs = self._parse_extraction_result(result.extracted_content, use_llm=True)

                    if not page_jobs:
                        logger.info(f"[Crawl4AI] No jobs found on page {page_num + 1}, might be end of results")
                        # Check if we got any content at all
                        if result.html and len(result.html) < 5000:
                            logger.warning("[Crawl4AI] Page content very small, possible blocking")
                        
                        # If we successfully loaded the page but found no jobs, it might be the end of results
                        # OR it might be a soft block (captcha/login wall that didn't trigger a navigation error)
                        # We'll stop for now to be safe
                        return jobs[:max_results]

                    jobs.extend(page_jobs)
                    logger.info(f"[Crawl4AI] Found {len(page_jobs)} jobs on page {page_num + 1} (total: {len(jobs)})")

                    # Layer 2 & 6: Mark proxy as successful and increment counters
                    if self.current_proxy:
                        self.proxy_rotator.mark_success(self.current_proxy)
                    self.pages_since_proxy_rotation += 1
                    self.pages_scraped_in_session += 1

                    # Layer 4: Smart delay between pages
                    await self._smart_delay(page_num, cloudflare_detected=cloudflare_detected_this_page)

                    page_num += 1
                    break # Success, exit retry loop

                except Exception as e:
                    logger.error(f"[Crawl4AI] Error scraping page {page_num + 1} (attempt {retry_count + 1}/{max_retries}): {type(e).__name__}: {e}")
                    retry_count += 1
                    if retry_count >= max_retries:
                        logger.error(f"[Crawl4AI] Failed to scrape page {page_num + 1} after {max_retries} retries")
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            return jobs[:max_results]
                    
                    # Exponential backoff
                    wait_time = 2 ** retry_count * 5  # Increased backoff: 10, 20, 40 seconds
                    await asyncio.sleep(wait_time)

        # Post-processing: Fetch company metadata for unique companies
        # Post-processing: Fetch company metadata for unique companies
        # unique_companies = {}
        # for job in jobs:
        #     if job.company_website and 'indeed.com/cmp/' in job.company_website:
        #         unique_companies[job.company_website] = None

        # logger.info(f"[Crawl4AI] extracting metadata for {len(unique_companies)} companies...")
        
        # for company_url in unique_companies:
        #     try:
        #         metadata = await self.extract_company_metadata(company_url)
        #         unique_companies[company_url] = metadata
        #         # Random delay between company pages
        #         await asyncio.sleep(random.uniform(2, 5))
        #     except Exception as e:
        #         logger.error(f"[Crawl4AI] Failed to extract metadata for {company_url}: {e}")

        # Enrich jobs with company metadata
        enriched_jobs = []
        for job in jobs:
            # if job.company_website and job.company_website in unique_companies:
            #     metadata = unique_companies[job.company_website]
            #     if metadata:
            #         # Create EnrichedJob
            #         enriched_job = EnrichedJob.from_job_listing(
            #             job,
            #             company_size=metadata.get('company_size'),
            #             industry=metadata.get('industry'),
            #             headquarters_location=metadata.get('headquarters'),
            #             company_website=metadata.get('website_url') or job.company_website # Prefer official site if found
            #         )
            #         enriched_jobs.append(enriched_job)
            #     else:
            #         enriched_jobs.append(job)
            # else:
            enriched_jobs.append(job)

        logger.info(f"[Crawl4AI] Search complete. Total jobs found: {len(enriched_jobs)}")
        return enriched_jobs[:max_results]

    def _build_search_url(
        self,
        query: str,
        location: str,
        page_num: int,
        remote_only: bool
    ) -> str:
        """Build Indeed search URL with filters"""
        params = {
            'q': query,
            'l': location,
            'start': page_num * 10,
        }

        if remote_only:
            params['sc'] = '0kf:attr(DSQF7);'  # Indeed's remote filter

        return f"{self.base_url}/jobs?{urlencode(params)}"

    def _parse_extraction_result(
        self,
        extracted_content: str,
        use_llm: bool = False
    ) -> List[JobListing]:
        """Convert Crawl4AI extraction results to JobListing objects"""
        if not extracted_content:
            return []

        try:
            data = json.loads(extracted_content)

            # Handle different response structures
            if use_llm and isinstance(data, dict) and 'jobs' in data:
                items = data['jobs']
            elif isinstance(data, list):
                items = data
            else:
                logger.warning(f"[Crawl4AI] Unexpected extraction format: {type(data)}")
                return []

            jobs = []
            for item in items:
                try:
                    logger.debug(f"[Crawl4AI] Raw scraped item: {json.dumps(item, indent=2, default=str)}")
                    job = self._item_to_job_listing(item)
                    if job:
                        logger.debug(f"[Crawl4AI] Parsed JobListing: {job}")
                    if job and job.title:  # Only add jobs with at least a title
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[Crawl4AI] Failed to parse job item: {e}")
                    continue

            return jobs

        except json.JSONDecodeError as e:
            logger.error(f"[Crawl4AI] Failed to parse extracted content: {e}")
            return []

    def _item_to_job_listing(self, item: Dict[str, Any]) -> Optional[JobListing]:
        """Convert extraction item to JobListing object"""
        title = (item.get('title') or '').strip()
        if not title:
            return None

        company = (item.get('company') or 'Unknown').strip()
        location = (item.get('location') or 'Remote').strip()
        description = (item.get('description') or '').strip()

        # Build job URL
        job_key = item.get('job_key')
        job_url = item.get('job_url', '')
        if job_key and not job_url:
            job_url = f"{self.base_url}/viewjob?jk={job_key}"
        elif job_url and not job_url.startswith('http'):
            job_url = f"{self.base_url}{job_url}"

        # Parse posted date
        posted_date = self._parse_posted_date(item.get('posted_date', ''))

        # Parse salary
        salary_min, salary_max = self._parse_salary(item)

        # Determine remote status
        is_remote = item.get('is_remote', False) or 'remote' in location.lower()
        remote_type = 'Remote' if is_remote else None

        # Build company URL
        # Build company URL
        company_url = item.get('company_url')
        
        # Prefer the direct extracted URL from JS interaction
        company_url_direct = item.get('company_url_direct')
        if company_url_direct:
             company_url = company_url_direct
        elif company_url and not company_url.startswith('http'):
            company_url = f"{self.base_url}{company_url}"

        return JobListing(
            title=title,
            company=company,
            location=location,
            description=description,
            url=job_url,
            posted_date=posted_date,
            board_source=JobBoard.INDEED,
            company_website=company_url,  # Indeed company page for now
            salary_min=salary_min,
            salary_max=salary_max,
            remote_type=remote_type,
        )

    def _parse_posted_date(self, date_text: str) -> datetime:
        """Parse Indeed's relative date format (e.g., '2 days ago')"""
        if not date_text:
            return datetime.now()

        date_text = date_text.lower().strip()

        # Handle "PostedJust posted" or similar concatenated strings
        date_text = date_text.replace('posted', '').strip()

        if not date_text or date_text == "just" or 'today' in date_text:
            return datetime.now()

        # Extract number from text
        match = re.search(r'(\d+)', date_text)
        if not match:
            return datetime.now()

        number = int(match.group(1))

        if 'hour' in date_text:
            return datetime.now() - timedelta(hours=number)
        elif 'day' in date_text:
            return datetime.now() - timedelta(days=number)
        elif 'week' in date_text:
            return datetime.now() - timedelta(weeks=number)
        elif 'month' in date_text:
            return datetime.now() - timedelta(days=number * 30)
        else:
            return datetime.now()

    def _parse_salary(self, item: Dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
        """Parse salary information from extraction item"""
        # Check for pre-parsed values (from LLM extraction)
        if item.get('salary_min') is not None:
            return float(item['salary_min']), float(item.get('salary_max') or item['salary_min'])

        salary_text = item.get('salary') or item.get('salary_text') or ''
        if not salary_text:
            return None, None

        # Extract numbers from salary text
        # Handles: "$50,000 - $70,000 a year", "$25 - $35 an hour", "$80K - $100K"
        numbers = re.findall(r'\$?([\d,]+(?:\.\d{2})?)\s*[kK]?', salary_text)

        if not numbers:
            return None, None

        values = []
        for num in numbers:
            num_clean = num.replace(',', '')
            try:
                val = float(num_clean)
                # Check if it's in thousands (K notation)
                if 'k' in salary_text.lower() and val < 1000:
                    val *= 1000
                # Check if it's hourly (convert to annual)
                if 'hour' in salary_text.lower() and val < 500:
                    val *= 2080  # 40 hours * 52 weeks
                values.append(val)
            except ValueError:
                continue

        if len(values) >= 2:
            return min(values), max(values)
        elif len(values) == 1:
            return values[0], values[0]

        return None, None

    async def get_job_details(self, job_url: str) -> Optional[JobListing]:
        """
        Fetch full job details from individual job page

        This can be enhanced to extract full job descriptions using LLM
        """
        logger.debug(f"[Crawl4AI] get_job_details not fully implemented: {job_url}")
        return None

    async def extract_company_website(self, company_page_url: str) -> Optional[str]:
        """
        Extract company's actual website from Indeed company profile page

        Uses LLM extraction for more accurate results
        """
        if not company_page_url:
            return None

        # Ensure we have LLM strategy for this
        if not self.llm_strategy:
            self.llm_strategy = self._create_llm_strategy()

        if not self.llm_strategy:
            logger.warning("[Crawl4AI] No LLM strategy available for company website extraction")
            return await self._extract_company_website_css(company_page_url)

        try:

            # Create specialized extraction strategy for company pages
            company_schema = {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string"},
                    "website_url": {
                        "type": "string",
                        "description": "Company's official website URL (NOT indeed.com or linkedin.com)"
                    },
                    "industry": {"type": "string"},
                    "company_size": {"type": "string"},
                    "headquarters": {"type": "string"}
                }
            }

            # Use same API key and provider logic as main extraction
            api_key = (
                os.getenv('OPENROUTER_API_KEY') or
                os.getenv('OPENAI_API_KEY') or
                os.getenv('ANTHROPIC_API_KEY')
            )

            if self.llm_model:
                provider = self.llm_model
            elif os.getenv('OPENROUTER_API_KEY'):
                provider = "openrouter/openai/gpt-4o-mini"
            elif os.getenv('ANTHROPIC_API_KEY'):
                provider = "anthropic/claude-sonnet-4-20250514"
            else:
                provider = self.llm_provider

            company_strategy = LLMExtractionStrategy(
                provider=provider,
                api_token=api_key,
                schema=company_schema,
                extraction_type="schema",
                instruction="""
                Find the company's official website URL from this Indeed company profile page.
                Look for:
                1. Links labeled "Website", "Company website", or "Visit website"
                2. External links in the company info section
                3. URLs mentioned in company description
                Do NOT return indeed.com, linkedin.com, glassdoor.com, or other job board URLs.
                Return the actual company domain (e.g., company.com).
                """
            )

            config = CrawlerRunConfig(
                extraction_strategy=company_strategy,
                magic=True,
                wait_until="domcontentloaded",
                delay_before_return_html=1.5,
            )

            result = await self.crawler.arun(url=company_page_url, config=config)

            if result.success and result.extracted_content:
                data = json.loads(result.extracted_content)
                website = data.get('website_url')
                if website and 'indeed.com' not in website.lower():
                    logger.info(f"[Crawl4AI] Extracted company website: {website}")
                    return website

        except Exception as e:
            logger.warning(f"[Crawl4AI] LLM extraction failed for company website: {e}")

        # Fallback to CSS extraction
        return await self._extract_company_website_css(company_page_url)

    async def _extract_company_website_css(self, company_page_url: str) -> Optional[str]:
        """Fallback CSS-based company website extraction"""
        try:
            schema = {
                "name": "Company Website",
                "baseSelector": "body",
                "fields": [
                    {
                        "name": "website_links",
                        "selector": "a[href]:not([href*='indeed.com']):not([href*='linkedin.com'])",
                        "type": "attribute",
                        "attribute": "href",
                        "multiple": True
                    }
                ]
            }

            config = CrawlerRunConfig(
                extraction_strategy=JsonCssExtractionStrategy(schema=schema),
                magic=True,
                wait_until="domcontentloaded",
            )

            result = await self.crawler.arun(url=company_page_url, config=config)

            if result.success and result.extracted_content:
                data = json.loads(result.extracted_content)
                links = data[0].get('website_links', []) if data else []

                # Filter for likely company websites
                for link in links:
                    if link and link.startswith('http') and \
                       'indeed.com' not in link and \
                       'linkedin.com' not in link and \
                       'glassdoor.com' not in link:
                        return link

        except Exception as e:
            logger.warning(f"[Crawl4AI] CSS extraction failed for company website: {e}")

        return None

    async def extract_company_metadata(self, company_page_url: str) -> Dict[str, Any]:
        """
        Extract detailed company metadata from Indeed company profile
        """
        if not company_page_url:
            return {}

        logger.info(f"[Crawl4AI] Visiting company profile: {company_page_url}")

        # Ensure we have LLM strategy for this
        if not self.llm_strategy:
            self.llm_strategy = self._create_llm_strategy()

        if not self.llm_strategy:
            logger.warning("[Crawl4AI] No LLM strategy available for company metadata extraction")
            return {}

        try:
            company_schema = {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string"},
                    "website_url": {
                        "type": "string",
                        "description": "Company's official website URL"
                    },
                    "industry": {"type": "string"},
                    "company_size": {"type": "string", "description": "e.g. 1000-5000 employees"},
                    "headquarters": {"type": "string"}
                }
            }

            # Reuse provider logic
            api_key = (
                os.getenv('OPENROUTER_API_KEY') or
                os.getenv('OPENAI_API_KEY') or
                os.getenv('ANTHROPIC_API_KEY')
            )
            
            # Determine provider
            if self.llm_model:
                provider = self.llm_model
            elif os.getenv('OPENROUTER_API_KEY'):
                provider = "openrouter/openai/gpt-4o-mini"
            elif os.getenv('ANTHROPIC_API_KEY'):
                provider = "anthropic/claude-sonnet-4-20250514"
            else:
                provider = self.llm_provider

            company_strategy = LLMExtractionStrategy(
                provider=provider,
                api_token=api_key,
                schema=company_schema,
                extraction_type="schema",
                instruction="""
                Extract company profile information.
                Look for:
                - Official website URL (not indeed/linkedin)
                - Industry (e.g. Technology, Healthcare)
                - Company size (number of employees)
                - Headquarters location
                """
            )

            config = CrawlerRunConfig(
                extraction_strategy=company_strategy,
                magic=True,
                wait_until="domcontentloaded",
                delay_before_return_html=2.0,
            )

            result = await self.crawler.arun(url=company_page_url, config=config)

            if result.success and result.extracted_content:
                data = json.loads(result.extracted_content)
                logger.info(f"[Crawl4AI] Extracted company metadata: {data}")
                return data

        except Exception as e:
            logger.warning(f"[Crawl4AI] LLM extraction failed for company metadata: {e}")

        return {}
