"""Database storage and operations"""
from typing import List, Optional
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker, Session, joinedload
from datetime import datetime, timedelta
from loguru import logger

from .models import Base, Job, Company, TeamMember, JobBoardEnum
from ..models import JobListing, EnrichedJob, JobBoard, CompanyProfile


class JobStorage:
    """Handle job database operations"""

    def __init__(self, database_url: str = "sqlite:///jobs.db"):
        """
        Initialize database connection

        Args:
            database_url: SQLAlchemy database URL
        """
        self.engine = create_engine(database_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        logger.info(f"Database initialized: {database_url}")

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()

    def save_jobs(self, jobs: List[JobListing]) -> int:
        """
        Save job listings to database

        Args:
            jobs: List of JobListing objects

        Returns:
            Number of jobs saved (excluding duplicates)
        """
        session = self.get_session()
        saved_count = 0

        try:
            for job in jobs:
                # Check if job already exists
                existing = session.query(Job).filter_by(id=job.id).first()

                if existing:
                    logger.debug(f"Job already exists: {job.id}")
                    continue

                # Convert JobListing to Job model
                db_job = Job(
                    id=job.id,
                    title=job.title,
                    company=job.company,
                    location=job.location,
                    description=job.description,
                    url=job.url,
                    posted_date=job.posted_date,
                    board_source=JobBoardEnum[job.board_source.name],
                    salary_min=job.salary_min,
                    salary_max=job.salary_max,
                    job_type=job.job_type,
                    remote_type=job.remote_type,
                    scraped_at=job.scraped_at
                )

                session.add(db_job)
                saved_count += 1

            session.commit()
            logger.info(f"Saved {saved_count} new jobs (skipped {len(jobs) - saved_count} duplicates)")
            return saved_count

        except Exception as e:
            session.rollback()
            logger.error(f"Error saving jobs: {e}")
            raise
        finally:
            session.close()

    def get_jobs(
        self,
        limit: int = 100,
        min_taiwan_team: int = 0,
        enriched_only: bool = False
    ) -> List[Job]:
        """
        Retrieve jobs from database

        Args:
            limit: Maximum number of jobs to return
            min_taiwan_team: Minimum Taiwan team members
            enriched_only: Only return enriched jobs

        Returns:
            List of Job model objects
        """
        session = self.get_session()

        try:
            query = session.query(Job)

            if enriched_only:
                query = query.filter(Job.enriched_at.isnot(None))

            if min_taiwan_team > 0:
                query = query.filter(Job.taiwan_team_count >= min_taiwan_team)

            # Order by ranking score (desc), then posted date (desc)
            query = query.order_by(Job.ranking_score.desc(), Job.posted_date.desc())

            jobs = query.limit(limit).all()
            return jobs

        finally:
            session.close()

    def save_company(self, company: CompanyProfile) -> bool:
        """
        Save or update company profile

        Args:
            company: CompanyProfile object

        Returns:
            True if saved successfully
        """
        session = self.get_session()

        try:
            existing = session.query(Company).filter_by(id=company.id).first()

            if existing:
                # Update existing company
                existing.name = company.name
                existing.linkedin_url = company.linkedin_url
                existing.website = company.website
                existing.industry = company.industry
                existing.company_size = company.company_size
                existing.headquarters_location = company.headquarters_location
                existing.description = company.description
                existing.total_employees = company.total_employees
                existing.taiwan_employee_count = company.taiwan_employee_count
                existing.enriched_at = company.enriched_at
                existing.source = company.source
                logger.debug(f"Updated company: {company.name}")
            else:
                # Create new company
                db_company = Company(
                    id=company.id,
                    name=company.name,
                    linkedin_url=company.linkedin_url,
                    website=company.website,
                    industry=company.industry,
                    company_size=company.company_size,
                    headquarters_location=company.headquarters_location,
                    description=company.description,
                    total_employees=company.total_employees,
                    taiwan_employee_count=company.taiwan_employee_count,
                    enriched_at=company.enriched_at,
                    source=company.source
                )
                session.add(db_company)
                logger.debug(f"Created company: {company.name}")

            # Save Taiwan team members
            if company.taiwan_employees:
                # Delete existing team members
                session.query(TeamMember).filter_by(company_id=company.id).delete()

                # Add new team members
                for member in company.taiwan_employees:
                    team_member = TeamMember(
                        company_id=company.id,
                        name=member.get('name'),
                        title=member.get('title'),
                        location=member.get('location'),
                        city=member.get('city'),
                        country=member.get('country', 'Taiwan'),
                        linkedin_url=member.get('linkedin_url')
                    )
                    session.add(team_member)

            session.commit()
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"Error saving company: {e}")
            return False
        finally:
            session.close()

    def get_company_by_name(self, name: str, max_age_days: int = 30) -> Optional[Company]:
        """
        Get company by name if recently enriched

        Args:
            name: Company name
            max_age_days: Maximum age of enrichment data in days

        Returns:
            Company object if found and recent, None otherwise
        """
        session = self.get_session()

        try:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)

            company = session.query(Company).options(
                joinedload(Company.team_members)
            ).filter(
                and_(
                    Company.name == name,
                    Company.enriched_at >= cutoff_date
                )
            ).first()

            return company

        finally:
            session.close()

    def update_job_enrichment(
        self,
        job_id: str,
        company_id: str,
        taiwan_team_count: int,
        ranking_score: float,
        **kwargs
    ) -> bool:
        """
        Update job with enrichment data

        Args:
            job_id: Job ID
            company_id: Company ID
            taiwan_team_count: Number of Taiwan team members
            ranking_score: Calculated ranking score
            **kwargs: Additional fields to update

        Returns:
            True if updated successfully
        """
        session = self.get_session()

        try:
            job = session.query(Job).filter_by(id=job_id).first()

            if not job:
                logger.warning(f"Job not found: {job_id}")
                return False

            job.company_id = company_id
            job.taiwan_team_count = taiwan_team_count
            job.ranking_score = ranking_score
            job.enriched_at = datetime.now()

            # Update additional fields
            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)

            session.commit()
            logger.debug(f"Updated job enrichment: {job_id}")
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"Error updating job enrichment: {e}")
            return False
        finally:
            session.close()

    def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Delete jobs older than specified days

        Args:
            days: Age threshold in days

        Returns:
            Number of jobs deleted
        """
        session = self.get_session()

        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted = session.query(Job).filter(Job.scraped_at < cutoff_date).delete()
            session.commit()
            logger.info(f"Deleted {deleted} old jobs")
            return deleted

        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting old jobs: {e}")
            return 0
        finally:
            session.close()
