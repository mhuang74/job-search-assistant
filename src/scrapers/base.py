"""Base scraper abstraction"""
from abc import ABC, abstractmethod
from typing import List, Optional
import asyncio
import random
from loguru import logger
from fake_useragent import UserAgent

from ..models import JobListing, JobBoard


class BaseScraper(ABC):
    """Base scraper with common functionality"""

    def __init__(self, board: JobBoard, config: dict = None):
        self.board = board
        self.config = config or {}
        self.user_agent = UserAgent()

    @abstractmethod
    async def search(
        self,
        query: str,
        location: str = "",
        max_results: int = 50,
        remote_only: bool = False
    ) -> List[JobListing]:
        """Search for jobs - must be implemented by subclass"""
        pass

    @abstractmethod
    async def get_job_details(self, job_url: str) -> Optional[JobListing]:
        """Get detailed job information - must be implemented"""
        pass

    def _get_random_user_agent(self) -> str:
        """Get random user agent to avoid detection"""
        try:
            return self.user_agent.random
        except Exception:
            # Fallback to a realistic default
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    async def _random_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Add random delay to mimic human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
