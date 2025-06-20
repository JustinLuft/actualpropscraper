# File: scraper/__init__.py
"""
Modular Web Scraper Framework
A flexible, extensible web scraping system with support for multiple websites
"""

__version__ = "1.0.0"
__author__ = "Web Scraper Team"

from .base_scraper import BaseScraper
from .alpha_capital_scraper import AlphaCapitalScraper
from .scraper_factory import ScraperFactory
from .config import Config

__all__ = ['BaseScraper', 'AlphaCapitalScraper', 'ScraperFactory', 'Config']
