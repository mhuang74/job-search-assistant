"""Tests for job deduplication logic"""
import pytest
from datetime import datetime
from src.utils.deduplicator import JobDeduplicator
from src.models import JobListing, JobBoard


def create_test_job(
    title="Software Engineer",
    company="Test Corp",
    location="Remote",
    url="https://indeed.com/viewjob?jk=abc123",
    job_id=None
):
    """Helper to create test job listings"""
    return JobListing(
        id=job_id,
        title=title,
        company=company,
        location=location,
        description="Test job description",
        url=url,
        posted_date=datetime.now(),
        board_source=JobBoard.INDEED,
        scraped_at=datetime.now()
    )


class TestURLDeduplication:
    """Test URL-based deduplication (critical after bug fix)"""

    def test_different_indeed_jobs_with_different_jk_params(self):
        """Different Indeed jobs should NOT be deduplicated (regression test for URL bug)"""
        jobs = [
            create_test_job(
                title="Director of Engineering",
                company="Company A",
                url="https://indeed.com/viewjob?jk=abc123"
            ),
            create_test_job(
                title="VP of Engineering",
                company="Company B",
                url="https://indeed.com/viewjob?jk=xyz789"
            ),
            create_test_job(
                title="Engineering Manager",
                company="Company C",
                url="https://indeed.com/viewjob?jk=def456"
            ),
        ]

        result = JobDeduplicator.deduplicate_jobs(jobs)

        # Should keep all 3 jobs (different jk= parameters)
        assert len(result) == 3, "Different Indeed jobs should not be deduplicated"

    def test_identical_urls_are_deduplicated(self):
        """Jobs with identical URLs should be deduplicated"""
        jobs = [
            create_test_job(
                title="Software Engineer",
                company="Company A",
                url="https://indeed.com/viewjob?jk=abc123"
            ),
            create_test_job(
                title="Software Engineer",  # Same job reposted
                company="Company A",
                url="https://indeed.com/viewjob?jk=abc123"  # Exact same URL
            ),
        ]

        result = JobDeduplicator.deduplicate_jobs(jobs)

        # Should keep only 1 job
        assert len(result) == 1, "Jobs with identical URLs should be deduplicated"

    def test_empty_url_does_not_cause_deduplication(self):
        """Jobs with empty URLs should not be deduplicated"""
        jobs = [
            create_test_job(title="Job 1", company="Company A", url=""),
            create_test_job(title="Job 2", company="Company B", url=""),
            create_test_job(title="Job 3", company="Company C", url=""),
        ]

        result = JobDeduplicator.deduplicate_jobs(jobs)

        # Should keep all jobs (no URL to compare)
        assert len(result) == 3, "Jobs with empty URLs should not be deduplicated by URL"


class TestExactIDDeduplication:
    """Test exact ID-based deduplication"""

    def test_same_id_is_deduplicated(self):
        """Jobs with same ID should be deduplicated"""
        jobs = [
            create_test_job(job_id="job123", title="Job A"),
            create_test_job(job_id="job123", title="Job A"),  # Duplicate
        ]

        result = JobDeduplicator.deduplicate_jobs(jobs)

        assert len(result) == 1, "Jobs with same ID should be deduplicated"

    def test_different_ids_are_not_deduplicated(self):
        """Jobs with different IDs should not be deduplicated"""
        jobs = [
            create_test_job(
                job_id="job123",
                title="Job A",
                url="https://indeed.com/viewjob?jk=job123"
            ),
            create_test_job(
                job_id="job456",
                title="Job B",
                url="https://indeed.com/viewjob?jk=job456"
            ),
            create_test_job(
                job_id="job789",
                title="Job C",
                url="https://indeed.com/viewjob?jk=job789"
            ),
        ]

        result = JobDeduplicator.deduplicate_jobs(jobs)

        assert len(result) == 3, "Jobs with different IDs should not be deduplicated"


class TestFuzzyDeduplication:
    """Test fuzzy matching deduplication"""

    def test_fuzzy_key_creation(self):
        """Test fuzzy key normalization"""
        job1 = create_test_job(title="Senior Software Engineer", company="Test Corp")
        job2 = create_test_job(title="Sr. Software Engineer", company="Test Corp")

        key1 = JobDeduplicator._create_fuzzy_key(job1)
        key2 = JobDeduplicator._create_fuzzy_key(job2)

        # "Senior" and "Sr." should both normalize to "sr"
        assert key1 == key2, "Senior and Sr. should create same fuzzy key"

    def test_fuzzy_deduplication_senior_variations(self):
        """Jobs with Senior/Sr variations should be deduplicated"""
        jobs = [
            create_test_job(
                title="Senior Software Engineer",
                company="Test Corp",
                url="https://indeed.com/viewjob?jk=abc123"
            ),
            create_test_job(
                title="Sr. Software Engineer",
                company="Test Corp",
                url="https://indeed.com/viewjob?jk=xyz789"  # Different URL
            ),
        ]

        result = JobDeduplicator.deduplicate_jobs(jobs)

        # Should deduplicate to 1 (same company, similar title)
        assert len(result) == 1, "Senior/Sr variations should be deduplicated"

    def test_fuzzy_different_companies_not_deduplicated(self):
        """Same title at different companies should NOT be deduplicated"""
        jobs = [
            create_test_job(
                title="Software Engineer",
                company="Company A",
                url="https://indeed.com/viewjob?jk=abc123"
            ),
            create_test_job(
                title="Software Engineer",
                company="Company B",
                url="https://indeed.com/viewjob?jk=xyz789"
            ),
        ]

        result = JobDeduplicator.deduplicate_jobs(jobs)

        # Should keep both (different companies)
        assert len(result) == 2, "Same title at different companies should not be deduplicated"

    def test_fuzzy_remote_keyword_ignored(self):
        """'Remote' keyword should be ignored in fuzzy matching"""
        jobs = [
            create_test_job(
                title="Software Engineer - Remote",
                company="Test Corp",
                url="https://indeed.com/viewjob?jk=abc123"
            ),
            create_test_job(
                title="Software Engineer",
                company="Test Corp",
                url="https://indeed.com/viewjob?jk=xyz789"
            ),
        ]

        result = JobDeduplicator.deduplicate_jobs(jobs)

        # Should deduplicate (remote keyword ignored)
        assert len(result) == 1, "Remote keyword should be ignored in fuzzy matching"


class TestDeduplicationOrder:
    """Test that newer jobs are preferred"""

    def test_newer_jobs_preferred(self):
        """When deduplicating, newer jobs should be kept"""
        from datetime import timedelta

        now = datetime.now()
        older = now - timedelta(days=5)

        jobs = [
            create_test_job(
                title="Software Engineer",
                company="Company A",
                url="https://indeed.com/viewjob?jk=abc123"
            ),
            create_test_job(
                title="Software Engineer",
                company="Company A",
                url="https://indeed.com/viewjob?jk=abc123"  # Same URL
            ),
        ]

        # Set different scraped_at times
        jobs[0].scraped_at = older
        jobs[1].scraped_at = now

        result = JobDeduplicator.deduplicate_jobs(jobs)

        # Should keep the newer one
        assert len(result) == 1
        assert result[0].scraped_at == now, "Newer job should be preferred"


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_list(self):
        """Empty list should return empty list"""
        result = JobDeduplicator.deduplicate_jobs([])
        assert result == [], "Empty list should return empty list"

    def test_single_job(self):
        """Single job should be returned as-is"""
        jobs = [create_test_job(title="Software Engineer")]
        result = JobDeduplicator.deduplicate_jobs(jobs)

        assert len(result) == 1, "Single job should be returned"

    def test_all_duplicates(self):
        """If all jobs are duplicates, should return only one"""
        jobs = [
            create_test_job(title="Job A", company="Company", url="https://example.com/job1"),
            create_test_job(title="Job A", company="Company", url="https://example.com/job1"),
            create_test_job(title="Job A", company="Company", url="https://example.com/job1"),
        ]

        result = JobDeduplicator.deduplicate_jobs(jobs)

        assert len(result) == 1, "All duplicates should deduplicate to 1"


class TestRealWorldScenario:
    """Test with real-world job data scenarios"""

    def test_indeed_scraping_scenario(self):
        """
        Test the exact scenario that was buggy:
        - Multiple different jobs from Indeed
        - All have /viewjob path but different jk= parameters
        - Should NOT be deduplicated
        """
        jobs = [
            create_test_job(
                title="Director of Engineering",
                company="Coffee Meets Bagel",
                url="https://indeed.com/viewjob?jk=abc123"
            ),
            create_test_job(
                title="Engineering Director",
                company="Care Continuity",
                url="https://indeed.com/viewjob?jk=def456"
            ),
            create_test_job(
                title="Director of Product",
                company="Learning Pool",
                url="https://indeed.com/viewjob?jk=ghi789"
            ),
            create_test_job(
                title="Associate Director of Engineering",
                company="Kryterion Inc",
                url="https://indeed.com/viewjob?jk=jkl012"
            ),
            create_test_job(
                title="Director, Operations Engineering",
                company="Radial, Inc.",
                url="https://indeed.com/viewjob?jk=mno345"
            ),
        ]

        result = JobDeduplicator.deduplicate_jobs(jobs)

        # Should keep all 5 jobs (all different companies and job keys)
        assert len(result) == 5, f"Expected 5 unique jobs, got {len(result)}"

        # Verify all different companies are present
        companies = {job.company for job in result}
        assert len(companies) == 5, "Should have 5 different companies"
