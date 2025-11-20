"""Data models for job search assistant"""
from .job import JobListing, EnrichedJob, JobBoard
from .company import CompanyProfile

__all__ = ['JobListing', 'EnrichedJob', 'JobBoard', 'CompanyProfile']
