"""Tests for data models"""
import pytest
from datetime import datetime
from src.models import JobListing, JobBoard


class TestJobListingIDGeneration:
    """Test job ID generation logic"""

    def test_generate_id_from_attributes(self):
        """ID should be generated from company, title, and location"""
        job = JobListing(
            id=None,
            title="Software Engineer",
            company="Test Corp",
            location="San Francisco",
            description="Test description",
            url="https://example.com/job1",
            posted_date=datetime.now(),
            board_source=JobBoard.INDEED,
            scraped_at=datetime.now()
        )

        job_id = job.generate_id()

        assert job_id is not None, "ID should be generated"
        assert len(job_id) == 16, "ID should be 16 characters (MD5 hash truncated)"

    def test_same_job_same_id(self):
        """Same job attributes should generate same ID"""
        job1 = JobListing(
            id=None,
            title="Software Engineer",
            company="Test Corp",
            location="San Francisco",
            description="Description 1",
            url="https://example.com/job1",
            posted_date=datetime.now(),
            board_source=JobBoard.INDEED,
            scraped_at=datetime.now()
        )

        job2 = JobListing(
            id=None,
            title="Software Engineer",
            company="Test Corp",
            location="San Francisco",
            description="Description 2",  # Different description
            url="https://example.com/job2",  # Different URL
            posted_date=datetime.now(),
            board_source=JobBoard.INDEED,
            scraped_at=datetime.now()
        )

        # Same company, title, location → same ID
        assert job1.generate_id() == job2.generate_id(), \
            "Same company/title/location should generate same ID"

    def test_different_company_different_id(self):
        """Different company should generate different ID"""
        job1 = JobListing(
            id=None,
            title="Software Engineer",
            company="Company A",
            location="San Francisco",
            description="Test",
            url="https://example.com/job1",
            posted_date=datetime.now(),
            board_source=JobBoard.INDEED,
            scraped_at=datetime.now()
        )

        job2 = JobListing(
            id=None,
            title="Software Engineer",
            company="Company B",  # Different company
            location="San Francisco",
            description="Test",
            url="https://example.com/job1",
            posted_date=datetime.now(),
            board_source=JobBoard.INDEED,
            scraped_at=datetime.now()
        )

        assert job1.generate_id() != job2.generate_id(), \
            "Different companies should generate different IDs"

    def test_different_title_different_id(self):
        """Different title should generate different ID"""
        job1 = JobListing(
            id=None,
            title="Software Engineer",
            company="Test Corp",
            location="San Francisco",
            description="Test",
            url="https://example.com/job1",
            posted_date=datetime.now(),
            board_source=JobBoard.INDEED,
            scraped_at=datetime.now()
        )

        job2 = JobListing(
            id=None,
            title="Senior Software Engineer",  # Different title
            company="Test Corp",
            location="San Francisco",
            description="Test",
            url="https://example.com/job1",
            posted_date=datetime.now(),
            board_source=JobBoard.INDEED,
            scraped_at=datetime.now()
        )

        assert job1.generate_id() != job2.generate_id(), \
            "Different titles should generate different IDs"

    def test_different_location_different_id(self):
        """Different location should generate different ID"""
        job1 = JobListing(
            id=None,
            title="Software Engineer",
            company="Test Corp",
            location="San Francisco",
            description="Test",
            url="https://example.com/job1",
            posted_date=datetime.now(),
            board_source=JobBoard.INDEED,
            scraped_at=datetime.now()
        )

        job2 = JobListing(
            id=None,
            title="Software Engineer",
            company="Test Corp",
            location="New York",  # Different location
            description="Test",
            url="https://example.com/job1",
            posted_date=datetime.now(),
            board_source=JobBoard.INDEED,
            scraped_at=datetime.now()
        )

        assert job1.generate_id() != job2.generate_id(), \
            "Different locations should generate different IDs"

    def test_id_case_insensitive(self):
        """ID generation should be case-insensitive"""
        job1 = JobListing(
            id=None,
            title="Software Engineer",
            company="Test Corp",
            location="San Francisco",
            description="Test",
            url="https://example.com/job1",
            posted_date=datetime.now(),
            board_source=JobBoard.INDEED,
            scraped_at=datetime.now()
        )

        job2 = JobListing(
            id=None,
            title="SOFTWARE ENGINEER",  # Different case
            company="TEST CORP",  # Different case
            location="SAN FRANCISCO",  # Different case
            description="Test",
            url="https://example.com/job1",
            posted_date=datetime.now(),
            board_source=JobBoard.INDEED,
            scraped_at=datetime.now()
        )

        assert job1.generate_id() == job2.generate_id(), \
            "ID generation should be case-insensitive"


class TestJobBoardEnum:
    """Test JobBoard enum"""

    def test_indeed_value(self):
        """Test Indeed enum value"""
        assert JobBoard.INDEED.value == "indeed"

    def test_enum_string_representation(self):
        """Test enum can be converted to string"""
        assert str(JobBoard.INDEED) == "JobBoard.INDEED"
