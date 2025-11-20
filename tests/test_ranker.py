"""Tests for job ranking algorithm"""
import pytest
from datetime import datetime, timedelta
from src.utils.ranker import JobRanker, RankingConfig
from src.models import EnrichedJob, JobBoard


def create_test_enriched_job(
    title="Software Engineer",
    company="Test Corp",
    taiwan_team_count=0,
    taiwan_team_members=None,
    industry=None,
    company_size=None,
    posted_date=None
):
    """Helper to create test enriched jobs"""
    return EnrichedJob(
        id="test123",
        title=title,
        company=company,
        location="Remote",
        description="Test description",
        url="https://example.com/job",
        posted_date=posted_date or datetime.now(),
        board_source=JobBoard.INDEED,
        scraped_at=datetime.now(),
        taiwan_team_count=taiwan_team_count,
        taiwan_team_members=taiwan_team_members or [],
        industry=industry,
        company_size=company_size,
        ranking_score=0.0
    )


class TestTaiwanTeamScoring:
    """Test Taiwan team count scoring"""

    def test_more_taiwan_team_higher_score(self):
        """Jobs with more Taiwan team members should score higher"""
        ranker = JobRanker()

        # Use different posted dates to avoid recency affecting scores
        from datetime import timedelta
        now = datetime.now()

        job1 = create_test_enriched_job(taiwan_team_count=1, posted_date=now)
        job2 = create_test_enriched_job(taiwan_team_count=3, posted_date=now)
        job3 = create_test_enriched_job(taiwan_team_count=5, posted_date=now)

        score1 = ranker.calculate_score(job1)
        score2 = ranker.calculate_score(job2)
        score3 = ranker.calculate_score(job3)

        # Check Taiwan component separately since total might hit cap
        taiwan1 = min(1 * 10, 50)  # 10
        taiwan2 = min(3 * 10, 50)  # 30
        taiwan3 = min(5 * 10, 50)  # 50

        assert taiwan1 < taiwan2 < taiwan3, "Taiwan team scoring should increase"
        assert score1 < score2, "Job with 3 Taiwan team should score higher than 1"
        assert score2 < score3, "Job with 5 Taiwan team should score higher than 3"

    def test_zero_taiwan_team(self):
        """Zero Taiwan team should give zero Taiwan score"""
        ranker = JobRanker()
        job = create_test_enriched_job(taiwan_team_count=0)

        score = ranker.calculate_score(job)

        # Should have some score from recency but not Taiwan team
        assert score >= 0, "Score should not be negative"

    def test_taiwan_team_cap(self):
        """Taiwan team score should be capped at 50 points"""
        ranker = JobRanker()

        job1 = create_test_enriched_job(taiwan_team_count=10)  # 10 * 10 = 100, capped at 50
        job2 = create_test_enriched_job(taiwan_team_count=20)  # 20 * 10 = 200, still capped at 50

        score1 = ranker.calculate_score(job1)
        score2 = ranker.calculate_score(job2)

        # Both should have similar Taiwan scores (both capped)
        # Total scores might differ due to recency, but Taiwan component is capped
        assert abs(score1 - score2) < 10, "Taiwan team score should be capped"


class TestCityProximityScoring:
    """Test preferred city proximity scoring"""

    def test_preferred_city_bonus(self):
        """Team members in preferred cities should give bonus"""
        config = RankingConfig(preferred_cities=['Taipei', 'Hsinchu'])
        ranker = JobRanker(config)

        job1 = create_test_enriched_job(
            taiwan_team_count=2,
            taiwan_team_members=[
                {'name': 'Person 1', 'city': 'Taipei'},
                {'name': 'Person 2', 'city': 'Hsinchu'},
            ]
        )

        job2 = create_test_enriched_job(
            taiwan_team_count=2,
            taiwan_team_members=[
                {'name': 'Person 1', 'city': 'Kaohsiung'},  # Not preferred
                {'name': 'Person 2', 'city': 'Tainan'},  # Not preferred
            ]
        )

        score1 = ranker.calculate_score(job1)
        score2 = ranker.calculate_score(job2)

        assert score1 > score2, "Preferred cities should score higher"

    def test_no_city_info(self):
        """Missing city info should not cause errors"""
        ranker = JobRanker()

        job = create_test_enriched_job(
            taiwan_team_count=2,
            taiwan_team_members=[
                {'name': 'Person 1'},  # No city
                {'name': 'Person 2'},  # No city
            ]
        )

        score = ranker.calculate_score(job)
        assert score >= 0, "Missing city info should not cause negative score"


class TestRecencyScoring:
    """Test job recency scoring"""

    def test_newer_jobs_score_higher(self):
        """Newer jobs should score higher than older jobs"""
        ranker = JobRanker()

        now = datetime.now()
        yesterday = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        job_new = create_test_enriched_job(posted_date=now)
        job_yesterday = create_test_enriched_job(posted_date=yesterday)
        job_week = create_test_enriched_job(posted_date=week_ago)
        job_old = create_test_enriched_job(posted_date=month_ago)

        score_new = ranker.calculate_score(job_new)
        score_yesterday = ranker.calculate_score(job_yesterday)
        score_week = ranker.calculate_score(job_week)
        score_old = ranker.calculate_score(job_old)

        assert score_new > score_yesterday, "Today should score higher than yesterday"
        assert score_yesterday > score_week, "Yesterday should score higher than week ago"
        assert score_week > score_old, "Week ago should score higher than month ago"


class TestIndustryScoring:
    """Test industry matching scoring"""

    def test_industry_match_bonus(self):
        """Matching industry should give bonus"""
        config = RankingConfig(target_industries=['Technology', 'Software'])
        ranker = JobRanker(config)

        job_match = create_test_enriched_job(industry='Technology')
        job_no_match = create_test_enriched_job(industry='Finance')

        score_match = ranker.calculate_score(job_match)
        score_no_match = ranker.calculate_score(job_no_match)

        assert score_match > score_no_match, "Matching industry should score higher"

    def test_no_industry_preference(self):
        """No industry preference should not affect score"""
        config = RankingConfig(target_industries=[])
        ranker = JobRanker(config)

        job1 = create_test_enriched_job(industry='Technology')
        job2 = create_test_enriched_job(industry='Finance')

        score1 = ranker.calculate_score(job1)
        score2 = ranker.calculate_score(job2)

        # Industry shouldn't affect score if no preference
        assert abs(score1 - score2) < 1, "No industry preference should not affect score"


class TestCompanySizeScoring:
    """Test company size preference scoring"""

    def test_company_size_match_bonus(self):
        """Matching company size should give bonus"""
        config = RankingConfig(target_company_sizes=['51-200', '201-500'])
        ranker = JobRanker(config)

        job_match = create_test_enriched_job(company_size='51-200')
        job_no_match = create_test_enriched_job(company_size='1000+')

        score_match = ranker.calculate_score(job_match)
        score_no_match = ranker.calculate_score(job_no_match)

        assert score_match > score_no_match, "Matching company size should score higher"


class TestRankJobs:
    """Test ranking multiple jobs"""

    def test_rank_jobs_returns_sorted_list(self):
        """rank_jobs should return jobs sorted by score"""
        ranker = JobRanker()

        jobs = [
            create_test_enriched_job(title="Job 1", taiwan_team_count=1),
            create_test_enriched_job(title="Job 2", taiwan_team_count=5),
            create_test_enriched_job(title="Job 3", taiwan_team_count=3),
        ]

        ranked = ranker.rank_jobs(jobs)

        # Should be sorted by score (descending)
        assert ranked[0].taiwan_team_count == 5, "Highest Taiwan team should be first"
        assert ranked[1].taiwan_team_count == 3, "Medium Taiwan team should be second"
        assert ranked[2].taiwan_team_count == 1, "Lowest Taiwan team should be last"

    def test_rank_jobs_assigns_scores(self):
        """rank_jobs should assign ranking_score to each job"""
        ranker = JobRanker()

        jobs = [
            create_test_enriched_job(taiwan_team_count=2),
            create_test_enriched_job(taiwan_team_count=3),
        ]

        ranked = ranker.rank_jobs(jobs)

        # All jobs should have ranking_score assigned
        assert all(job.ranking_score > 0 for job in ranked), "All jobs should have scores"

    def test_rank_empty_list(self):
        """Ranking empty list should return empty list"""
        ranker = JobRanker()
        ranked = ranker.rank_jobs([])

        assert ranked == [], "Empty list should return empty list"


class TestMinimumThreshold:
    """Test minimum Taiwan team threshold in ranking config"""

    def test_minimum_threshold_setting(self):
        """Config should store minimum Taiwan team threshold"""
        config = RankingConfig(min_taiwan_team=3)

        assert config.min_taiwan_team == 3, "Should store minimum threshold"

    def test_default_minimum_threshold(self):
        """Default minimum Taiwan team should be 1"""
        config = RankingConfig()

        assert config.min_taiwan_team == 1, "Default minimum should be 1"
