"""Job deduplication logic"""
import re
from typing import List, Set
from urllib.parse import urlparse
from loguru import logger

from ..models import JobListing


class JobDeduplicator:
    """Intelligent job deduplication across multiple boards"""

    @staticmethod
    def deduplicate_jobs(jobs: List[JobListing]) -> List[JobListing]:
        """
        Remove duplicate jobs using multiple matching strategies
        Priority: exact match > fuzzy match > keep all

        Args:
            jobs: List of JobListing objects

        Returns:
            Deduplicated list of jobs
        """
        if not jobs:
            return []

        unique_jobs = []
        seen_ids = set()
        seen_fuzzy = set()

        # Sort by scraped_at (newer first) to prefer fresh listings
        sorted_jobs = sorted(jobs, key=lambda j: j.scraped_at, reverse=True)

        for job in sorted_jobs:
            # Strategy 1: Exact ID match (company + title + location)
            if job.id in seen_ids:
                logger.debug(f"Duplicate (exact ID): {job.title} at {job.company}")
                continue

            # Strategy 2: Fuzzy match (normalized title + company)
            fuzzy_key = JobDeduplicator._create_fuzzy_key(job)
            if fuzzy_key in seen_fuzzy:
                logger.debug(f"Duplicate (fuzzy): {job.title} at {job.company}")
                continue

            # Strategy 3: URL match (some boards cross-post with same URL)
            if JobDeduplicator._is_duplicate_url(job, unique_jobs):
                logger.debug(f"Duplicate (URL): {job.title} at {job.company}")
                continue

            unique_jobs.append(job)
            seen_ids.add(job.id)
            seen_fuzzy.add(fuzzy_key)

        logger.info(f"Deduplicated: {len(jobs)} -> {len(unique_jobs)} jobs")
        return unique_jobs

    @staticmethod
    def _create_fuzzy_key(job: JobListing) -> str:
        """Create normalized key for fuzzy matching"""

        def normalize(text: str) -> str:
            """Normalize: lowercase, remove special chars, remove extra spaces"""
            text = text.lower()
            text = re.sub(r'[^\w\s]', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text

        title = normalize(job.title)
        company = normalize(job.company)

        # Remove common variations
        title = title.replace('senior', 'sr').replace('junior', 'jr')
        title = title.replace('remote', '').replace('hybrid', '')
        title = title.replace('  ', ' ').strip()

        return f"{company}:{title}"

    @staticmethod
    def _is_duplicate_url(job: JobListing, existing_jobs: List[JobListing]) -> bool:
        """Check if URL already exists (handles redirects)"""
        if not job.url:
            return False

        # For Indeed URLs with job key, compare the full URL (not just path)
        # because path is always /viewjob but query params differ
        for existing in existing_jobs:
            if not existing.url:
                continue

            # Exact URL match (most reliable)
            if job.url == existing.url:
                logger.debug(f"URL match: {job.url}")
                return True

        return False
