"""Main enrichment service with caching"""
import os
from typing import List, Optional
from datetime import datetime, timedelta
from loguru import logger

from .people_data_labs import PeopleDataLabsEnricher
from .coresignal import CoresignalEnricher
from ..models import JobListing, EnrichedJob, CompanyProfile
from ..database import JobStorage
from ..utils import JobRanker, RankingConfig


class EnrichmentService:
    """
    Orchestrate job enrichment with LinkedIn data

    Features:
    - Automatic company matching
    - Taiwan team member identification
    - Caching to minimize API costs
    - Ranking based on Taiwan team presence
    """

    def __init__(
        self,
        service: str = "peopledatalabs",
        api_key: Optional[str] = None,
        cache_days: int = 30
    ):
        """
        Initialize enrichment service

        Args:
            service: "peopledatalabs" or "coresignal"
            api_key: API key for the service
            cache_days: Number of days to cache company data
        """
        self.service = service
        self.cache_days = cache_days
        self.storage = JobStorage(os.getenv('DATABASE_URL', 'sqlite:///jobs.db'))

        # Initialize API client
        if service == "peopledatalabs":
            self.api_key = api_key or os.getenv('PEOPLEDATALABS_API_KEY')
            if not self.api_key:
                raise ValueError("PEOPLEDATALABS_API_KEY not set")
            self.enricher = PeopleDataLabsEnricher(self.api_key)
        elif service == "coresignal":
            self.api_key = api_key or os.getenv('CORESIGNAL_API_KEY')
            if not self.api_key:
                raise ValueError("CORESIGNAL_API_KEY not set")
            self.enricher = CoresignalEnricher(self.api_key)
        else:
            raise ValueError(f"Unknown service: {service}")

        logger.info(f"Enrichment service initialized: {service}")

    async def __aenter__(self):
        await self.enricher.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.enricher.__aexit__(exc_type, exc_val, exc_tb)

    async def enrich_jobs(
        self,
        jobs: List[JobListing],
        ranking_config: Optional[RankingConfig] = None
    ) -> List[EnrichedJob]:
        """
        Enrich jobs with LinkedIn company data

        Args:
            jobs: List of JobListing objects
            ranking_config: Ranking configuration

        Returns:
            List of EnrichedJob objects, sorted by ranking score
        """
        enriched_jobs = []
        companies_processed = set()

        logger.info(f"Enriching {len(jobs)} jobs...")

        for job in jobs:
            # Skip if company already processed (batch optimization)
            if job.company in companies_processed:
                logger.debug(f"Skipping duplicate company: {job.company}")
                # Try to get company from cache
                cached_company = self.storage.get_company_by_name(
                    job.company,
                    max_age_days=self.cache_days
                )
                if cached_company:
                    enriched_job = self._create_enriched_job(job, cached_company)
                    enriched_jobs.append(enriched_job)
                else:
                    # Add job without enrichment
                    enriched_jobs.append(EnrichedJob.from_job_listing(job))
                continue

            companies_processed.add(job.company)

            # Check cache first
            cached_company = self.storage.get_company_by_name(
                job.company,
                max_age_days=self.cache_days
            )

            if cached_company:
                logger.info(f"Using cached data for: {job.company}")
                enriched_job = self._create_enriched_job(job, cached_company)
                enriched_jobs.append(enriched_job)
                continue

            # Fetch from API
            try:
                company_profile = await self._get_company_with_taiwan_team(job.company)

                if company_profile:
                    # Save to cache
                    self.storage.save_company(company_profile)

                    # Create enriched job
                    enriched_job = self._create_enriched_job_from_profile(job, company_profile)
                    enriched_jobs.append(enriched_job)

                    logger.info(
                        f"Enriched: {job.company} - "
                        f"{company_profile.taiwan_employee_count} Taiwan team members"
                    )
                else:
                    # Company not found, add without enrichment
                    logger.warning(f"Company not found: {job.company}")
                    enriched_jobs.append(EnrichedJob.from_job_listing(job))

            except Exception as e:
                logger.error(f"Error enriching {job.company}: {e}")
                enriched_jobs.append(EnrichedJob.from_job_listing(job))

        # Rank jobs
        if ranking_config:
            ranker = JobRanker(ranking_config)
            ranked_jobs = ranker.rank_jobs(enriched_jobs)
        else:
            # Use default ranking
            ranker = JobRanker()
            ranked_jobs = ranker.rank_jobs(enriched_jobs)

        # Save enrichment data to database
        for enriched_job in ranked_jobs:
            if enriched_job.company_id:
                self.storage.update_job_enrichment(
                    job_id=enriched_job.id,
                    company_id=enriched_job.company_id,
                    taiwan_team_count=enriched_job.taiwan_team_count,
                    ranking_score=enriched_job.ranking_score,
                    company_size=enriched_job.company_size,
                    industry=enriched_job.industry,
                    headquarters_location=enriched_job.headquarters_location
                )

        logger.info(f"Enrichment complete: {len(ranked_jobs)} jobs ranked")
        return ranked_jobs

    async def _get_company_with_taiwan_team(self, company_name: str) -> Optional[CompanyProfile]:
        """
        Get company profile with Taiwan team members

        Args:
            company_name: Company name

        Returns:
            CompanyProfile with Taiwan employee data
        """
        # Get company profile
        company_profile = await self.enricher.get_company_profile(company_name)

        if not company_profile:
            return None

        # Get Taiwan employees
        if self.service == "peopledatalabs":
            taiwan_employees = await self.enricher.search_employees_in_taiwan(company_name)
        elif self.service == "coresignal":
            taiwan_employees = await self.enricher.get_employees_in_taiwan(
                company_profile.id
            )
        else:
            taiwan_employees = []

        # Update company profile with Taiwan data
        company_profile.taiwan_employee_count = len(taiwan_employees)
        company_profile.taiwan_employees = taiwan_employees
        company_profile.enriched_at = datetime.now()

        return company_profile

    def _create_enriched_job(self, job: JobListing, cached_company) -> EnrichedJob:
        """Create EnrichedJob from cached company data"""
        # Get team members
        team_members = [
            {
                'name': tm.name,
                'title': tm.title,
                'location': tm.location,
                'city': tm.city,
                'country': tm.country,
                'linkedin_url': tm.linkedin_url
            }
            for tm in cached_company.team_members
        ]

        return EnrichedJob.from_job_listing(
            job,
            company_id=cached_company.id,
            company_size=cached_company.company_size,
            industry=cached_company.industry,
            headquarters_location=cached_company.headquarters_location,
            taiwan_team_count=cached_company.taiwan_employee_count,
            taiwan_team_members=team_members,
            enriched_at=cached_company.enriched_at
        )

    def _create_enriched_job_from_profile(
        self,
        job: JobListing,
        company_profile: CompanyProfile
    ) -> EnrichedJob:
        """Create EnrichedJob from CompanyProfile"""
        return EnrichedJob.from_job_listing(
            job,
            company_id=company_profile.id,
            company_size=company_profile.company_size,
            industry=company_profile.industry,
            headquarters_location=company_profile.headquarters_location,
            taiwan_team_count=company_profile.taiwan_employee_count,
            taiwan_team_members=company_profile.taiwan_employees,
            enriched_at=company_profile.enriched_at
        )
