"""Job ranking algorithm"""
from datetime import datetime
from typing import List
from dataclasses import dataclass
from loguru import logger

from ..models import EnrichedJob


@dataclass
class RankingConfig:
    """Configuration for job ranking"""
    taiwan_team_weight: float = 10.0
    same_city_weight: float = 5.0
    industry_match_weight: float = 3.0
    company_size_match_weight: float = 3.0
    recency_weight: float = 5.0

    target_industries: List[str] = None
    target_company_sizes: List[str] = None
    preferred_cities: List[str] = None
    min_taiwan_team: int = 1

    def __post_init__(self):
        self.target_industries = self.target_industries or []
        self.target_company_sizes = self.target_company_sizes or []
        self.preferred_cities = self.preferred_cities or ['Taipei', 'Hsinchu', 'Taichung']


class JobRanker:
    """Rank jobs based on multiple factors"""

    def __init__(self, config: RankingConfig = None):
        self.config = config or RankingConfig()

    def calculate_score(self, job: EnrichedJob) -> float:
        """
        Calculate ranking score for a job

        Args:
            job: EnrichedJob object

        Returns:
            Ranking score (higher is better)
        """
        score = 0.0

        # Critical: Taiwan team presence (0-50 points)
        taiwan_count = job.taiwan_team_count or 0
        score += min(taiwan_count * self.config.taiwan_team_weight, 50)

        # Proximity bonus (0-20 points)
        if self.config.preferred_cities and job.taiwan_team_members:
            city_matches = sum(
                1 for member in job.taiwan_team_members
                if member.get('city') in self.config.preferred_cities
            )
            score += min(city_matches * self.config.same_city_weight, 20)

        # Industry match (0-15 points)
        if self.config.target_industries and job.industry:
            if any(industry.lower() in job.industry.lower()
                   for industry in self.config.target_industries):
                score += self.config.industry_match_weight * 5

        # Company size match (0-10 points)
        if self.config.target_company_sizes and job.company_size:
            if job.company_size in self.config.target_company_sizes:
                score += self.config.company_size_match_weight * 3

        # Freshness (0-5 points)
        if job.posted_date:
            days_old = (datetime.now() - job.posted_date).days
            freshness_score = max(0, self.config.recency_weight - (days_old / 7))
            score += freshness_score

        return round(score, 2)

    def rank_jobs(self, jobs: List[EnrichedJob]) -> List[EnrichedJob]:
        """
        Rank jobs and sort by score

        Args:
            jobs: List of EnrichedJob objects

        Returns:
            Sorted list of jobs with ranking_score set
        """
        # Filter by minimum Taiwan team requirement
        filtered_jobs = [
            job for job in jobs
            if (job.taiwan_team_count or 0) >= self.config.min_taiwan_team
        ]

        # Calculate scores
        for job in filtered_jobs:
            job.ranking_score = self.calculate_score(job)

        # Sort by score (descending)
        ranked = sorted(filtered_jobs, key=lambda x: x.ranking_score, reverse=True)

        logger.info(f"Ranked {len(ranked)} jobs (filtered {len(jobs) - len(ranked)} below threshold)")
        return ranked
