# scraper/base_scraper.py
from abc import ABC, abstractmethod
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time
import re
import logging
from typing import List, Dict, Optional
import json
import os

class BaseScraper(ABC):
    """Abstract base class for all website scrapers"""
    
    def __init__(self, headless: bool = True, timeout: int = 10):
        self.headless = headless
        self.timeout = timeout
        self.driver = None
        self.wait = None
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def setup_driver(self):
        """Initialize Chrome WebDriver"""
        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, self.timeout)
            self.logger.info("Chrome driver initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome driver: {e}")
            raise
            
    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            self.logger.info("Chrome driver closed")
            
    @abstractmethod
    def get_selectors(self) -> Dict[str, List[str]]:
        """Return CSS selectors for the specific website"""
        pass
        
    @abstractmethod
    def extract_account_info(self, element) -> Dict[str, str]:
        """Extract account information from a single element"""
        pass
        
    @abstractmethod
    def get_base_url(self) -> str:
        """Return the base URL of the website"""
        pass
        
    def scrape_website(self, url: Optional[str] = None) -> List[Dict[str, str]]:
        """Main scraping method"""
        if not url:
            url = self.get_base_url()
            
        try:
            self.setup_driver()
            self.logger.info(f"Starting to scrape: {url}")
            
            self.driver.get(url)
            time.sleep(5)  # Wait for page to load
            
            accounts_data = []
            selectors = self.get_selectors()
            
            # Try different selector strategies
            for selector_type, selector_list in selectors.items():
                self.logger.info(f"Trying {selector_type} selectors...")
                
                for selector in selector_list:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            self.logger.info(f"Found {len(elements)} elements with selector: {selector}")
                            
                            for element in elements:
                                account_info = self.extract_account_info(element)
                                if account_info and any(account_info.values()):
                                    accounts_data.append(account_info)
                            
                            if accounts_data:
                                break
                    except Exception as e:
                        self.logger.warning(f"Selector {selector} failed: {e}")
                        continue
                        
                if accounts_data:
                    break
                    
            # Fallback to page source analysis
            if not accounts_data:
                self.logger.info("Falling back to page source analysis...")
                accounts_data = self.extract_from_page_source()
                
            self.logger.info(f"Successfully scraped {len(accounts_data)} accounts")
            return accounts_data
            
        except Exception as e:
            self.logger.error(f"Error during scraping: {e}")
            return []
        finally:
            self.close_driver()
            
    def extract_from_page_source(self) -> List[Dict[str, str]]:
        """Fallback method to extract from page source"""
        try:
            page_source = self.driver.page_source
            return self.parse_page_source(page_source)
        except Exception as e:
            self.logger.error(f"Error in page source extraction: {e}")
            return []
            
    @abstractmethod
    def parse_page_source(self, page_source: str) -> List[Dict[str, str]]:
        """Parse page source for account information"""
        pass
        
    def save_to_csv(self, data: List[Dict[str, str]], filename: str = None):
        """Save data to CSV file"""
        if not data:
            self.logger.warning("No data to save!")
            return False
            
        if not filename:
            filename = f"{self.__class__.__name__.lower()}_data.csv"
            
        try:
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False)
            self.logger.info(f"Data saved to {filename} ({len(data)} records)")
            return True
        except Exception as e:
            self.logger.error(f"Error saving to CSV: {e}")
            return False


# scraper/alpha_capital_scraper.py
class AlphaCapitalScraper(BaseScraper):
    """Scraper for Alpha Capital Group website"""
    
    def get_base_url(self) -> str:
        return "https://alphacapitalgroup.uk/"
        
    def get_selectors(self) -> Dict[str, List[str]]:
        return {
            "account_cards": [
                ".account-card",
                ".trading-account", 
                ".plan-card",
                ".evaluation-card",
                "[data-testid*='account']"
            ],
            "generic_cards": [
                ".card",
                ".package", 
                ".tier",
                ".pricing-card"
            ],
            "containers": [
                ".container",
                ".section",
                ".plans-section"
            ]
        }
        
    def extract_account_info(self, element) -> Dict[str, str]:
        """Extract account information from element"""
        try:
            text = element.text.strip()
            if not text:
                return {}
                
            account_data = {
                'business_name': 'Alpha Capital Group',
                'account_size': self._extract_account_size(text),
                'sale_price': self._extract_sale_price(text),
                'funded_full_price': self._extract_funded_price(text),
                'discount_coupon_code': self._extract_discount_code(text),
                'trail_type': self._extract_trail_type(text),
                'trustpilot_score': self._extract_trustpilot_score(text),
                'profit_goal': self._extract_profit_goal(text)
            }
            
            return account_data
            
        except Exception as e:
            self.logger.error(f"Error extracting account info: {e}")
            return {}
            
    def _extract_account_size(self, text: str) -> str:
        """Extract account size from text"""
        patterns = [
            r'\$(\d+[kK])',
            r'(\d+[kK])\s*account',
            r'(\d+,?\d+)\s*account'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""
        
    def _extract_sale_price(self, text: str) -> str:
        """Extract sale price from text"""
        pattern = r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)'
        matches = re.findall(pattern, text)
        return matches[0] if matches else ""
        
    def _extract_funded_price(self, text: str) -> str:
        """Extract funded full price from text"""
        pattern = r'funded.*?\$(\d+(?:,\d{3})*(?:\.\d{2})?)'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else ""
        
    def _extract_discount_code(self, text: str) -> str:
        """Extract discount code from text"""
        patterns = [
            r'code[:\s]+([A-Z0-9]+)',
            r'discount[:\s]+(\d+%)',
            r'coupon[:\s]+([A-Z0-9]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""
        
    def _extract_trail_type(self, text: str) -> str:
        """Extract trail type from text"""
        patterns = [
            r'(one[- ]?step|two[- ]?step|three[- ]?step)',
            r'leverage[:\s]+(\d+:\d+)',
            r'(evaluation|instant|challenge)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""
        
    def _extract_trustpilot_score(self, text: str) -> str:
        """Extract Trustpilot score from text"""
        pattern = r'trustpilot.*?(\d+\.?\d*)'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else ""
        
    def _extract_profit_goal(self, text: str) -> str:
        """Extract profit goal from text"""
        patterns = [
            r'profit.*?(\d+%)',
            r'target.*?(\d+%)',
            r'goal.*?(\d+%)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""
        
    def parse_page_source(self, page_source: str) -> List[Dict[str, str]]:
        """Parse page source as fallback"""
        accounts_data = []
        
        # Extract all relevant data from page source
        amounts = re.findall(r'\$(\d+(?:,\d{3})*(?:\.\d{2})?|\d+[kK])', page_source)
        percentages = re.findall(r'(\d+(?:\.\d+)?%)', page_source)
        
        if amounts:
            for i, amount in enumerate(amounts[:5]):  # Limit to avoid duplicates
                account_data = {
                    'business_name': 'Alpha Capital Group',
                    'account_size': amount if 'k' in amount.lower() else '',
                    'sale_price': amount if 'k' not in amount.lower() else '',
                    'funded_full_price': '',
                    'discount_coupon_code': '',
                    'trail_type': '',
                    'trustpilot_score': '',
                    'profit_goal': percentages[i] if i < len(percentages) else ''
                }
                accounts_data.append(account_data)
                
        return accounts_data


# scraper/scraper_factory.py
class ScraperFactory:
    """Factory class to create scrapers for different websites"""
    
    _scrapers = {
        'alphacapitalgroup.uk': AlphaCapitalScraper,
        'alpha-capital': AlphaCapitalScraper,
        # Add more scrapers here as you create them
    }
    
    @classmethod
    def create_scraper(cls, website: str, **kwargs) -> BaseScraper:
        """Create a scraper instance for the specified website"""
        
        # Normalize website name
        website_key = website.lower()
        for key in cls._scrapers:
            if key in website_key:
                return cls._scrapers[key](**kwargs)
                
        raise ValueError(f"No scraper available for website: {website}")
    
    @classmethod
    def get_available_scrapers(cls) -> List[str]:
        """Return list of available scrapers"""
        return list(cls._scrapers.keys())
    
    @classmethod
    def register_scraper(cls, website: str, scraper_class):
        """Register a new scraper class"""
        cls._scrapers[website] = scraper_class


# scraper/config.py
import os
import json
from typing import Dict, List

class Config:
    """Configuration management for the scraper"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        
    def load_config(self) -> Dict:
        """Load configuration from file or environment variables"""
        config = {
            "websites": [],
            "output_dir": "output",
            "headless": True,
            "timeout": 10,
            "max_retries": 3,
            "delay_between_requests": 2
        }
        
        # Load from file if exists
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config)
            except Exception as e:
                print(f"Error loading config file: {e}")
                
        # Override with environment variables
        config["headless"] = os.getenv("HEADLESS", "true").lower() == "true"
        config["timeout"] = int(os.getenv("TIMEOUT", "10"))
        config["output_dir"] = os.getenv("OUTPUT_DIR", "output")
        
        # Load websites from environment variable
        websites_env = os.getenv("WEBSITES")
        if websites_env:
            config["websites"] = websites_env.split(",")
            
        return config
        
    def get_websites(self) -> List[str]:
        """Get list of websites to scrape"""
        return self.config.get("websites", [])
        
    def get_output_dir(self) -> str:
        """Get output directory"""
        return self.config.get("output_dir", "output")
        
    def is_headless(self) -> bool:
        """Check if running in headless mode"""
        return self.config.get("headless", True)
        
    def get_timeout(self) -> int:
        """Get timeout value"""
        return self.config.get("timeout", 10)


# main.py
import os
import sys
from datetime import datetime
from scraper.scraper_factory import ScraperFactory
from scraper.config import Config

def main():
    """Main function to run the scraping process"""
    
    # Load configuration
    config = Config()
    
    # Create output directory
    output_dir = config.get_output_dir()
    os.makedirs(output_dir, exist_ok=True)
    
    # Get websites to scrape
    websites = config.get_websites()
    if not websites:
        print("No websites configured to scrape!")
        sys.exit(1)
        
    print(f"Starting scraping process for {len(websites)} websites...")
    
    all_results = []
    
    for website in websites:
        try:
            print(f"\n{'='*50}")
            print(f"Scraping: {website}")
            print(f"{'='*50}")
            
            # Create scraper instance
            scraper = ScraperFactory.create_scraper(
                website,
                headless=config.is_headless(),
                timeout=config.get_timeout()
            )
            
            # Scrape the website
            results = scraper.scrape_website()
            
            if results:
                # Save individual website results
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{output_dir}/{website.replace('.', '_')}_{timestamp}.csv"
                scraper.save_to_csv(results, filename)
                
                # Add to combined results
                all_results.extend(results)
                print(f"✅ Successfully scraped {len(results)} records from {website}")
            else:
                print(f"❌ No data scraped from {website}")
                
        except Exception as e:
            print(f"❌ Error scraping {website}: {e}")
            continue
            
    # Save combined results
    if all_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_filename = f"{output_dir}/combined_results_{timestamp}.csv"
        
        import pandas as pd
        df = pd.DataFrame(all_results)
        df.to_csv(combined_filename, index=False)
        
        print(f"\n🎉 Scraping completed!")
        print(f"📊 Total records: {len(all_results)}")
        print(f"💾 Combined results saved to: {combined_filename}")
    else:
        print(f"\n⚠️ No data was scraped from any website!")
        sys.exit(1)

if __name__ == "__main__":
    main()
