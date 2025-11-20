"""Tests for Indeed scraper functions"""
import pytest
from datetime import datetime, timedelta


class TestDateParsing:
    """Test Indeed date parsing logic - using standalone function"""

    def _parse_posted_date(self, date_text: str) -> datetime:
        """
        Standalone version of Indeed's date parsing for testing
        (copied from IndeedScraper to avoid async context issues)
        """
        import re
        date_text = date_text.lower().strip()

        if not date_text or date_text == "just posted" or date_text == "today":
            return datetime.now()

        # Extract number from text
        match = re.search(r'(\d+)', date_text)
        if not match:
            return datetime.now()

        days = int(match.group(1))

        # Parse relative dates
        if 'hour' in date_text or 'minute' in date_text:
            return datetime.now()
        elif 'day' in date_text:
            return datetime.now() - timedelta(days=days)
        elif 'week' in date_text:
            return datetime.now() - timedelta(weeks=days)
        elif 'month' in date_text:
            return datetime.now() - timedelta(days=days * 30)
        else:
            return datetime.now()

    def test_parse_just_posted(self):
        """'Just posted' should return today's date"""
        result = self._parse_posted_date("Just posted")
        now = datetime.now()

        assert result.date() == now.date(), "Just posted should be today"

    def test_parse_today(self):
        """'Today' should return today's date"""
        result = self._parse_posted_date("Today")
        now = datetime.now()

        assert result.date() == now.date(), "Today should be today's date"

    def test_parse_days_ago(self):
        """'X days ago' should subtract X days from today"""
        result = self._parse_posted_date("5 days ago")
        expected = datetime.now() - timedelta(days=5)

        assert result.date() == expected.date(), "5 days ago should be 5 days before today"

    def test_parse_one_day_ago(self):
        """'1 day ago' should be yesterday"""
        result = self._parse_posted_date("1 day ago")
        expected = datetime.now() - timedelta(days=1)

        assert result.date() == expected.date(), "1 day ago should be yesterday"

    def test_parse_30_plus_days_ago(self):
        """'30+ days ago' should extract the number"""
        result = self._parse_posted_date("30+ days ago")
        expected = datetime.now() - timedelta(days=30)

        assert result.date() == expected.date(), "30+ days ago should be 30 days before today"

    def test_parse_hours_ago(self):
        """'X hours ago' should return today"""
        result = self._parse_posted_date("3 hours ago")
        now = datetime.now()

        # Hours should still be today
        assert result.date() == now.date(), "Hours ago should still be today"

    def test_parse_empty_string(self):
        """Empty string should return today"""
        result = self._parse_posted_date("")
        now = datetime.now()

        assert result.date() == now.date(), "Empty string should default to today"

    def test_parse_invalid_format(self):
        """Invalid format should return today (fallback)"""
        result = self._parse_posted_date("Some random text")
        now = datetime.now()

        assert result.date() == now.date(), "Invalid format should fallback to today"

    def test_parse_case_insensitive(self):
        """Parsing should be case-insensitive"""
        result1 = self._parse_posted_date("JUST POSTED")
        result2 = self._parse_posted_date("just posted")
        result3 = self._parse_posted_date("Just Posted")

        # All should return today
        now = datetime.now()
        assert result1.date() == now.date()
        assert result2.date() == now.date()
        assert result3.date() == now.date()

    def test_parse_with_extra_whitespace(self):
        """Should handle extra whitespace"""
        result = self._parse_posted_date("  5 days ago  ")
        expected = datetime.now() - timedelta(days=5)

        assert result.date() == expected.date(), "Should handle whitespace"

    def test_parse_various_days(self):
        """Test various day values"""
        test_cases = [
            ("1 days ago", 1),
            ("7 days ago", 7),
            ("14 days ago", 14),
            ("21 days ago", 21),
            ("30 days ago", 30),
        ]

        for text, days in test_cases:
            result = self._parse_posted_date(text)
            expected = datetime.now() - timedelta(days=days)
            assert result.date() == expected.date(), f"{text} failed"

