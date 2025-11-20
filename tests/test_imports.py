"""Test that all public APIs are importable from package level"""
import pytest


class TestPackageImports:
    """Test that imports work at package level (not just submodules)"""

    def test_utils_package_exports(self):
        """Test that src.utils exports all necessary classes"""
        # This is how the application code imports - through the package
        from src.utils import JobDeduplicator, JobRanker, RankingConfig

        # Verify classes are importable
        assert JobDeduplicator is not None
        assert JobRanker is not None
        assert RankingConfig is not None

    def test_models_package_exports(self):
        """Test that src.models exports all necessary classes"""
        from src.models import JobListing, EnrichedJob, JobBoard, CompanyProfile

        assert JobListing is not None
        assert EnrichedJob is not None
        assert JobBoard is not None
        assert CompanyProfile is not None

    def test_enrichment_package_exports(self):
        """Test that src.enrichment exports all necessary classes"""
        from src.enrichment import (
            PeopleDataLabsEnricher,
            CoresignalEnricher,
            EnrichmentService
        )

        assert PeopleDataLabsEnricher is not None
        assert CoresignalEnricher is not None
        assert EnrichmentService is not None

    def test_database_package_exports(self):
        """Test that src.database exports necessary classes"""
        from src.database import JobStorage

        assert JobStorage is not None


class TestDirectImportsStillWork:
    """Ensure direct imports from submodules also work (backward compatibility)"""

    def test_direct_import_from_ranker(self):
        """Direct import from submodule should work"""
        from src.utils.ranker import JobRanker, RankingConfig

        assert JobRanker is not None
        assert RankingConfig is not None

    def test_direct_import_from_deduplicator(self):
        """Direct import from submodule should work"""
        from src.utils.deduplicator import JobDeduplicator

        assert JobDeduplicator is not None
