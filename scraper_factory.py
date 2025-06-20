from typing import Dict, Type, List
from base_scraper import BaseScraper
from alpha_capital_scrapper import AlphaCapitalScraper

class ScraperFactory:
    """Enhanced factory class with better website matching"""
    
    _scrapers: Dict[str, Type[BaseScraper]] = {
        'alphacapitalgroup.uk': AlphaCapitalScraper,
        'alpha-capital': AlphaCapitalScraper,
        'alphacapital': AlphaCapitalScraper,
        # Add more scrapers here as you create them
        # 'example.com': ExampleScraper,
    }
    
    @classmethod
    def create_scraper(cls, website: str, **kwargs) -> BaseScraper:
        """Create a scraper instance for the specified website"""
        
        # Normalize website name
        website_key = website.lower().replace('www.', '').replace('https://', '').replace('http://', '')
        
        # Direct match first
        if website_key in cls._scrapers:
            return cls._scrapers[website_key](**kwargs)
            
        # Partial match
        for key, scraper_class in cls._scrapers.items():
            if key in website_key or website_key in key:
                return scraper_class(**kwargs)
                
        raise ValueError(f"No scraper available for website: {website}. Available scrapers: {list(cls._scrapers.keys())}")
    
    @classmethod
    def get_available_scrapers(cls) -> List[str]:
        """Return list of available scrapers"""
        return list(cls._scrapers.keys())
    
    @classmethod
    def register_scraper(cls, website: str, scraper_class: Type[BaseScraper]):
        """Register a new scraper class"""
        cls._scrapers[website] = scraper_class
        
    @classmethod
    def is_supported(cls, website: str) -> bool:
        """Check if website is supported"""
        try:
            cls.create_scraper(website)
            return True
        except ValueError:
            return False
