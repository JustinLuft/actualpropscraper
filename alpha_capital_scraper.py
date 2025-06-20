import re
import time
from bs4 import BeautifulSoup
from typing import Dict, List
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from base_scraper import BaseScraper

class AlphaCapitalScraper(BaseScraper):
    """Enhanced scraper for Alpha Capital Group website with JavaScript support"""
    
    def __init__(self):
        super().__init__()
        self.driver = None
        
    def get_base_url(self) -> str:
        return "https://alphacapitalgroup.uk/"
        
    def setup_driver(self):
        """Setup Selenium WebDriver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def scrape_accounts(self) -> List[Dict[str, str]]:
        """Main scraping method with JavaScript support"""
        if not self.driver:
            self.setup_driver()
            
        accounts_data = []
        
        try:
            self.driver.get(self.get_base_url())
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Wait for dynamic content to load
            time.sleep(3)
            
            # Get account size options
            account_sizes = self._get_account_sizes()
            
            # Scrape data for each account size and plan type
            for account_size in account_sizes:
                # Try different plan types (1 Step, 2 Step, 3 Step if available)
                plan_types = self._get_plan_types()
                
                for plan_type in plan_types:
                    account_data = self._scrape_specific_plan(account_size, plan_type)
                    if account_data and self._is_valid_data(account_data):
                        accounts_data.append(account_data)
                        
            return accounts_data
            
        except Exception as e:
            self.logger.error(f"Error during scraping: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
                
    def _get_account_sizes(self) -> List[str]:
        """Extract available account sizes from the page"""
        account_sizes = []
        
        try:
            # Look for account size buttons/options
            size_selectors = [
                "button[class*='size']",
                "div[class*='size']",
                ".account-size",
                "button:contains('$')",
                "[data-value*='000']"
            ]
            
            for selector in size_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        # Extract dollar amounts
                        size_match = re.search(r'\$(\d+,?\d*)', text)
                        if size_match:
                            size = size_match.group(1)
                            if size not in account_sizes:
                                account_sizes.append(size)
                except:
                    continue
                    
            # If no sizes found, look in the page source
            if not account_sizes:
                page_text = self.driver.page_source
                size_matches = re.findall(r'\$(\d+,\d{3})', page_text)
                account_sizes = list(set(size_matches))
                
            # Default sizes if nothing found (from screenshot)
            if not account_sizes:
                account_sizes = ['5,000', '10,000', '25,000', '50,000', '100,000', '200,000']
                
            return account_sizes[:6]  # Limit to reasonable number
            
        except Exception as e:
            self.logger.error(f"Error getting account sizes: {e}")
            return ['10,000', '50,000']  # Fallback
            
    def _get_plan_types(self) -> List[str]:
        """Get available plan types"""
        try:
            plan_types = []
            
            # Look for step buttons
            step_selectors = [
                "button:contains('Step')",
                ".step-button",
                "[class*='step']",
                "button[class*='plan']"
            ]
            
            for selector in step_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        if 'step' in text.lower():
                            plan_types.append(text)
                except:
                    continue
                    
            if not plan_types:
                plan_types = ['1 Step', '2 Step', '3 Step']
                
            return plan_types
            
        except Exception as e:
            self.logger.error(f"Error getting plan types: {e}")
            return ['assessment']
            
    def _scrape_specific_plan(self, account_size: str, plan_type: str) -> Dict[str, str]:
        """Scrape data for a specific account size and plan type"""
        try:
            # Try to click account size if it's a button
            self._click_account_size(account_size)
            time.sleep(1)
            
            # Try to click plan type if it's a button  
            self._click_plan_type(plan_type)
            time.sleep(1)
            
            # Now extract the data from the current state
            account_data = {
                'business_name': 'Alpha Capital Group',
                'account_size': account_size.replace(',', ''),
                'sale_price': self._extract_current_price(),
                'funded_full_price': self._extract_funded_price_from_page(),
                'discount_coupon_code': self._extract_discount_from_page(),
                'trail_type': self._normalize_plan_type(plan_type),
                'trustpilot_score': self._extract_trustpilot_from_page(),
                'profit_goal': self._extract_profit_target_from_page(),
                'scraped_at': datetime.now().isoformat()
            }
            
            return account_data
            
        except Exception as e:
            self.logger.error(f"Error scraping plan {plan_type} for {account_size}: {e}")
            return {}
            
    def _click_account_size(self, size: str):
        """Try to click on account size option"""
        try:
            # Look for buttons containing the size
            selectors = [
                f"button:contains('{size}')",
                f"button:contains('${size}')",
                f"[data-value='{size}']",
                f"[value='{size}']"
            ]
            
            for selector in selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element.is_displayed():
                        element.click()
                        return
                except:
                    continue
                    
        except Exception as e:
            self.logger.debug(f"Could not click account size {size}: {e}")
            
    def _click_plan_type(self, plan_type: str):
        """Try to click on plan type option"""
        try:
            selectors = [
                f"button:contains('{plan_type}')",
                f".step-button:contains('{plan_type}')",
                f"[data-plan='{plan_type.lower()}']"
            ]
            
            for selector in selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element.is_displayed():
                        element.click()
                        return
                except:
                    continue
                    
        except Exception as e:
            self.logger.debug(f"Could not click plan type {plan_type}: {e}")
            
    def _extract_current_price(self) -> str:
        """Extract the currently displayed price"""
        try:
            # Look for price displays (from screenshot: "Assessment Price: $97")
            price_selectors = [
                "[class*='price']",
                ".price-display",
                ".assessment-price",
                ".cost",
                ".fee"
            ]
            
            for selector in price_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text
                        price_match = re.search(r'\$(\d+(?:\.\d{2})?)', text)
                        if price_match:
                            price = price_match.group(1)
                            # Validate price range
                            if 50 <= float(price) <= 1000:
                                return price
                except:
                    continue
                    
            # Fallback: search entire page for price patterns
            page_text = self.driver.page_source
            price_matches = re.findall(r'(?:price|cost|fee)[:\s]*\$(\d+(?:\.\d{2})?)', page_text, re.IGNORECASE)
            for price in price_matches:
                if 50 <= float(price) <= 1000:
                    return price
                    
            return ""
            
        except Exception as e:
            self.logger.error(f"Error extracting price: {e}")
            return ""
            
    def _extract_funded_price_from_page(self) -> str:
        """Extract funded account price from current page"""
        try:
            page_text = self.driver.page_source
            patterns = [
                r'funded.*?\$(\d+(?:\.\d{2})?)',
                r'full.*?price.*?\$(\d+(?:\.\d{2})?)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    return match.group(1)
            return ""
            
        except Exception as e:
            return ""
            
    def _extract_discount_from_page(self) -> str:
        """Extract discount information from current page"""
        try:
            page_text = self.driver.page_source
            patterns = [
                r'(\d+%)\s*(?:off|discount)',
                r'save[:\s]+(\d+%)',
                r'discount[:\s]+(\d+%)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    return match.group(1)
            return ""
            
        except Exception as e:
            return ""
            
    def _extract_trustpilot_from_page(self) -> str:
        """Extract Trustpilot score from page"""
        try:
            page_text = self.driver.page_source
            patterns = [
                r'trustpilot.*?(\d+\.?\d*)',
                r'(\d+\.?\d*)\s*(?:stars?|rating)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    score = float(match.group(1))
                    if 1 <= score <= 5:
                        return str(score)
            return ""
            
        except Exception as e:
            return ""
            
    def _extract_profit_target_from_page(self) -> str:
        """Extract profit target from current page state"""
        try:
            # Look for profit target elements
            target_selectors = [
                "[class*='profit']",
                "[class*='target']", 
                ".sim-profit-target"
            ]
            
            for selector in target_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text
                        target_match = re.search(r'(\d+%)', text)
                        if target_match:
                            percentage = int(target_match.group(1).replace('%', ''))
                            if 1 <= percentage <= 50:
                                return target_match.group(1)
                except:
                    continue
                    
            # Fallback to page source search
            page_text = self.driver.page_source
            profit_matches = re.findall(r'(?:profit|target).*?(\d+%)', page_text, re.IGNORECASE)
            for match in profit_matches:
                percentage = int(match.replace('%', ''))
                if 1 <= percentage <= 50:
                    return match
                    
            return ""
            
        except Exception as e:
            return ""
            
    def _normalize_plan_type(self, plan_type: str) -> str:
        """Normalize plan type to consistent format"""
        plan_type = plan_type.lower().strip()
        if 'step' in plan_type:
            return 'assessment'
        elif 'instant' in plan_type or 'direct' in plan_type:
            return 'instant'
        elif 'evaluation' in plan_type:
            return 'evaluation'
        else:
            return 'assessment'
            
    def _is_valid_data(self, data: Dict[str, str]) -> bool:
        """Check if the scraped data contains meaningful information"""
        required_fields = ['account_size', 'sale_price']
        return any(data.get(field) for field in required_fields)
        
    def parse_page_source(self, page_source: str) -> List[Dict[str, str]]:
        """Fallback method for static HTML parsing"""
        # This method is kept for compatibility but main scraping now uses Selenium
        return self.scrape_accounts()
        
    def __del__(self):
        """Cleanup driver on object destruction"""
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
            except:
                pass
