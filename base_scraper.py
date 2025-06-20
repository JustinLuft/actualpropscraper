from abc import ABC, abstractmethod
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import time
import re
import logging
from typing import List, Dict, Optional, Any
import json
import os
import random
from datetime import datetime

class BaseScraper(ABC):
    """Abstract base class for all website scrapers"""
    
    def __init__(self, headless: bool = True, timeout: int = 30):
        self.headless = headless
        self.timeout = timeout
        self.driver = None
        self.wait = None
        self.config = self._load_config()
        self.setup_logging()
        
    def _load_config(self) -> Dict:
        """Load configuration from config.json"""
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "max_retries": 3,
                "delay_between_requests": 2,
                "user_agents": [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                ]
            }
        
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
        """Initialize Chrome WebDriver with enhanced options"""
        try:
            chrome_options = Options()
            
            # Basic options
            if self.headless:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Anti-detection options
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins-discovery")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Random user agent
            user_agents = self.config.get("user_agents", [])
            if user_agents:
                user_agent = random.choice(user_agents)
                chrome_options.add_argument(f"--user-agent={user_agent}")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": self.driver.execute_script("return navigator.userAgent").replace('Headless', '')
            })
            
            self.wait = WebDriverWait(self.driver, self.timeout)
            self.logger.info("Chrome driver initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome driver: {e}")
            raise
            
    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Chrome driver closed")
            except Exception as e:
                self.logger.warning(f"Error closing driver: {e}")
                
    def wait_for_page_load(self, additional_wait: int = 3):
        """Wait for page to fully load"""
        try:
            # Wait for document ready state
            self.wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            time.sleep(additional_wait)  # Additional wait for dynamic content
        except TimeoutException:
            self.logger.warning("Page load timeout, proceeding anyway")
            
    def handle_popups(self):
        """Handle common popups and overlays"""
        popup_selectors = [
            "button[aria-label*='close']",
            ".modal-close",
            ".popup-close",
            "[data-dismiss='modal']",
            ".cookie-accept",
            ".accept-cookies"
        ]
        
        for selector in popup_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    elements[0].click()
                    time.sleep(1)
                    self.logger.info(f"Closed popup with selector: {selector}")
            except Exception:
                continue
                
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
        """Main scraping method with retry logic"""
        if not url:
            url = self.get_base_url()
            
        max_retries = self.config.get("max_retries", 3)
        delay = self.config.get("delay_between_requests", 2)
        
        for attempt in range(max_retries):
            try:
                self.setup_driver()
                self.logger.info(f"Attempt {attempt + 1}/{max_retries}: Scraping {url}")
                
                self.driver.get(url)
                self.wait_for_page_load()
                self.handle_popups()
                
                accounts_data = self._extract_data()
                
                if accounts_data:
                    self.logger.info(f"Successfully scraped {len(accounts_data)} accounts")
                    return accounts_data
                else:
                    self.logger.warning(f"No data found on attempt {attempt + 1}")
                    
            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    self.logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
            finally:
                self.close_driver()
                
        self.logger.error(f"All {max_retries} attempts failed for {url}")
        return []
        
    def _extract_data(self) -> List[Dict[str, str]]:
        """Extract data using multiple strategies"""
        accounts_data = []
        selectors = self.get_selectors()
        
        # Strategy 1: Try specific selectors
        for selector_type, selector_list in selectors.items():
            self.logger.info(f"Trying {selector_type} selectors...")
            
            for selector in selector_list:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        self.logger.info(f"Found {len(elements)} elements with selector: {selector}")
                        
                        for element in elements:
                            try:
                                account_info = self.extract_account_info(element)
                                if account_info and any(v.strip() for v in account_info.values() if v):
                                    accounts_data.append(account_info)
                            except Exception as e:
                                self.logger.warning(f"Error extracting from element: {e}")
                                continue
                        
                        if accounts_data:
                            return accounts_data
                            
                except Exception as e:
                    self.logger.warning(f"Selector {selector} failed: {e}")
                    continue
                    
        # Strategy 2: Fallback to page source analysis
        if not accounts_data:
            self.logger.info("Falling back to page source analysis...")
            accounts_data = self.extract_from_page_source()
            
        return accounts_data
        
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
        
    def validate_data(self, data: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Validate and clean scraped data"""
        validated_data = []
        
        for item in data:
            # Remove empty items
            if not any(v.strip() for v in item.values() if v):
                continue
                
            # Clean data
            cleaned_item = {}
            for key, value in item.items():
                if value:
                    cleaned_item[key] = str(value).strip()
                else:
                    cleaned_item[key] = ""
                    
            validated_data.append(cleaned_item)
            
        # Remove duplicates
        seen = set()
        unique_data = []
        for item in validated_data:
            item_tuple = tuple(sorted(item.items()))
            if item_tuple not in seen:
                seen.add(item_tuple)
                unique_data.append(item)
                
        return unique_data
        
    def save_to_csv(self, data: List[Dict[str, str]], filename: str = None) -> bool:
        """Save data to CSV file with enhanced error handling"""
        if not data:
            self.logger.warning("No data to save!")
            return False
            
        # Validate data before saving
        validated_data = self.validate_data(data)
        
        if not validated_data:
            self.logger.warning("No valid data to save after validation!")
            return False
            
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.__class__.__name__.lower()}_{timestamp}.csv"
            
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
            
            df = pd.DataFrame(validated_data)
            df.to_csv(filename, index=False)
            self.logger.info(f"Data saved to {filename} ({len(validated_data)} records)")
            return True
        except Exception as e:
            self.logger.error(f"Error saving to CSV: {e}")
            return False
