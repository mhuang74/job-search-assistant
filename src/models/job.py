"""Job listing models"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List
import hashlib


class JobBoard(Enum):
    """Supported job boards"""
    INDEED = "indeed"
    LINKEDIN = "linkedin"
    REMOTEOK = "remoteok"
    WEWORKREMOTELY = "weworkremotely"


@dataclass
class JobListing:
    """Standardized job listing structure across all boards"""
    title: str
    company: str
    location: str
    description: str
    url: str
    posted_date: datetime
    board_source: JobBoard
    id: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[str] = None
    job_type: Optional[str] = None  # Full-time, Part-time, Contract
    remote_type: Optional[str] = None  # Remote, Hybrid, On-site
    scraped_at: datetime = field(default_factory=datetime.now)
    raw_html: Optional[str] = None  # Store for debugging

    def __post_init__(self):
        """Generate unique ID across boards for deduplication"""
        if not self.id:
            self.id = self.generate_id()

    def generate_id(self) -> str:
        """Create deterministic ID from job attributes"""
        key = f"{self.company}:{self.title}:{self.location}".lower()
        return hashlib.md5(key.encode()).hexdigest()[:16]


@dataclass
class EnrichedJob:
    """Job listing with LinkedIn enrichment data"""
    # Copy all fields from JobListing
    id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    posted_date: datetime
    board_source: JobBoard
    salary_min: Optional[float] = None
    salary_max: Optional[str] = None
    job_type: Optional[str] = None
    remote_type: Optional[str] = None
    scraped_at: datetime = field(default_factory=datetime.now)
    raw_html: Optional[str] = None

    # Enrichment fields
    company_id: Optional[str] = None
    company_size: Optional[str] = None
    industry: Optional[str] = None
    headquarters_location: Optional[str] = None
    taiwan_team_count: int = 0
    taiwan_team_members: List[dict] = field(default_factory=list)
    enriched_at: Optional[datetime] = None
    ranking_score: float = 0.0

    @classmethod
    def from_job_listing(cls, job: JobListing, **enrichment_data):
        """Create EnrichedJob from JobListing"""
        return cls(
            id=job.id,
            title=job.title,
            company=job.company,
            location=job.location,
            description=job.description,
            url=job.url,
            posted_date=job.posted_date,
            board_source=job.board_source,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            job_type=job.job_type,
            remote_type=job.remote_type,
            scraped_at=job.scraped_at,
            raw_html=job.raw_html,
            **enrichment_data
        )
