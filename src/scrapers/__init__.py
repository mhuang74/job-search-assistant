"""Job board scrapers"""
from .base import BaseScraper
from .indeed import IndeedScraper

__all__ = ['BaseScraper', 'IndeedScraper']
