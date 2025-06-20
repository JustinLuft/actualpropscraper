import re
import time
from bs4 import BeautifulSoup
from typing import Dict, List
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from base_scraper import BaseScraper

class AlphaCapitalScraper(BaseScraper):
    """Enhanced scraper for Alpha Capital Group website with JavaScript support"""
    
    def __init__(self, headless: bool = True, timeout: int = 30):
        super().__init__(headless, timeout)
        
    def get_base_url(self) -> str:
        return "https://alphacapitalgroup.uk/"
        
    def get_selectors(self) -> Dict[str, List[str]]:
        """Return CSS selectors optimized for Alpha Capital Group"""
        return {
            "primary_selectors": [
                # Price display areas
                "[class*='price']",
                ".assessment-price",
                ".price-display",
                ".cost-display",
                # Account size buttons/containers
                "button[class*='size']",
                "[data-value*='000']",
                ".account-size",
                # Plan containers
                ".plan-card",
                ".evaluation-card",
                ".tier-card",
                # Step buttons
                "button[class*='step']",
                ".step-button"
            ],
            "secondary_selectors": [
                # Generic containers that might hold pricing info
                ".card",
                ".pricing-tier", 
                ".plan-wrapper",
                ".package",
                ".product-card",
                # Form elements
                "form [class*='price']",
                ".form-group",
                # Table elements
                "table [class*='price']",
                "td, th"
            ],
            "fallback_selectors": [
                # Very generic containers
                "div[class*='plan']",
                "div[class*='price']",
                "div[class*='tier']",
                ".container .row > div",
                ".section > div"
            ]
        }
        
    def extract_account_info(self, element) -> Dict[str, str]:
        """Extract account information from element with enhanced logic"""
        try:
            text = element.text.strip() if hasattr(element, 'text') else str(element)
            
            if len(text) < 10:  # Skip elements with too little content
                return {}
                
            account_data = {
                'business_name': 'Alpha Capital Group',
                'account_size': self._extract_account_size(text),
                'sale_price': self._extract_sale_price(text),
                'funded_full_price': self._extract_funded_price(text),
                'discount_coupon_code': self._extract_discount_code(text),
                'trail_type': self._extract_trail_type(text),
                'trustpilot_score': self._extract_trustpilot_score(text),
                'profit_goal': self._extract_profit_goal(text),
                'scraped_at': datetime.now().isoformat()
            }
            
            return account_data
            
        except Exception as e:
            self.logger.error(f"Error extracting account info: {e}")
            return {}
            
    def scrape_website(self, url: str = None) -> List[Dict[str, str]]:
        """Override to add interactive scraping for Alpha Capital"""
        if not url:
            url = self.get_base_url()
            
        max_retries = self.config.get("max_retries", 3)
        delay = self.config.get("delay_between_requests", 2)
        
        for attempt in range(max_retries):
            try:
                self.setup_driver()
                self.logger.info(f"Attempt {attempt + 1}/{max_retries}: Scraping {url}")
                
                self.driver.get(url)
                self.wait_for_page_load(5)  # Extra wait for dynamic content
                self.handle_popups()
                
                # Alpha Capital specific: Interactive scraping
                accounts_data = self._scrape_interactive_data()
                
                if accounts_data:
                    self.logger.info(f"Successfully scraped {len(accounts_data)} accounts")
                    return self.validate_data(accounts_data)
                else:
                    # Fallback to standard extraction
                    accounts_data = self._extract_data()
                    if accounts_data:
                        return self.validate_data(accounts_data)
                    
                self.logger.warning(f"No data found on attempt {attempt + 1}")
                    
            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    self.logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= 2
            finally:
                self.close_driver()
                
        self.logger.error(f"All {max_retries} attempts failed for {url}")
        return []
        
    def _scrape_interactive_data(self) -> List[Dict[str, str]]:
        """Interactive scraping specific to Alpha Capital Group"""
        accounts_data = []
        
        try:
            # Get available account sizes and plan types
            account_sizes = self._get_account_sizes()
            plan_types = self._get_plan_types()
            
            self.logger.info(f"Found account sizes: {account_sizes}")
            self.logger.info(f"Found plan types: {plan_types}")
            
            # Try each combination
            for account_size in account_sizes[:5]:  # Limit to avoid too many requests
                for plan_type in plan_types[:3]:  # Limit plan types
                    try:
                        account_data = self._scrape_specific_combination(account_size, plan_type)
                        if account_data and self._is_valid_data(account_data):
                            accounts_data.append(account_data)
                            self.logger.info(f"Scraped data for {account_size} - {plan_type}")
                        
                        # Small delay between combinations
                        time.sleep(1)
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to scrape {account_size}-{plan_type}: {e}")
                        continue
                        
            return accounts_data
            
        except Exception as e:
            self.logger.error(f"Error in interactive scraping: {e}")
            return []
            
    def _get_account_sizes(self) -> List[str]:
        """Extract available account sizes"""
        account_sizes = []
        
        try:
            # Look for account size buttons/displays
            size_patterns = [
                r'\$(\d{1,3}(?:,\d{3})*)',  # $5,000, $10,000, etc.
                r'(\d+[kK])',  # 50K, 100K
                r'(\d+,\d{3})'  # 25,000
            ]
            
            page_text = self.driver.page_source
            
            for pattern in size_patterns:
                matches = re.findall(pattern, page_text)
                for match in matches:
                    if match and match not in account_sizes:
                        # Filter reasonable account sizes
                        size_num = int(match.replace(',', '').replace('K', '000').replace('k', '000'))
                        if 1000 <= size_num <= 1000000:  # Between $1K and $1M
                            account_sizes.append(match)
                            
            # Try clicking to find interactive elements
            size_selectors = [
                "button:contains('$')",
                "[class*='size'] button",
                "[data-value*='000']"
            ]
            
            for selector in size_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        size_match = re.search(r'\$?(\d+,?\d*)', text)
                        if size_match and size_match.group(1) not in account_sizes:
                            account_sizes.append(size_match.group(1))
                except:
                    continue
                    
            # Default fallback from screenshot
            if not account_sizes:
                account_sizes = ['5,000', '10,000', '25,000', '50,000', '100,000', '200,000']
                
            return account_sizes[:6]  # Limit results
            
        except Exception as e:
            self.logger.error(f"Error getting account sizes: {e}")
            return ['10,000', '50,000']  # Minimal fallback
            
    def _get_plan_types(self) -> List[str]:
        """Extract available plan types"""
        try:
            plan_types = []
            
            # Look for step buttons and plan types
            page_text = self.driver.page_source.lower()
            
            if '1 step' in page_text or 'one step' in page_text:
                plan_types.append('1 Step')
            if '2 step' in page_text or 'two step' in page_text:
                plan_types.append('2 Step')
            if '3 step' in page_text or 'three step' in page_text:
                plan_types.append('3 Step')
            if 'assessment' in page_text:
                plan_types.append('Assessment')
            if 'evaluation' in page_text:
                plan_types.append('Evaluation')
                
            # Try to find interactive elements
            step_selectors = [
                "button[class*='step']",
                ".step-button",
                "button:contains('Step')"
            ]
            
            for selector in step_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and text not in plan_types:
                            plan_types.append(text)
                except:
                    continue
                    
            return plan_types if plan_types else ['Assessment', '1 Step']
            
        except Exception as e:
            self.logger.error(f"Error getting plan types: {e}")
            return ['Assessment']
            
    def _scrape_specific_combination(self, account_size: str, plan_type: str) -> Dict[str, str]:
        """Scrape data for specific account size and plan type combination"""
        try:
            # Try to interact with the page to select this combination
            self._select_account_size(account_size)
            time.sleep(1)
            self._select_plan_type(plan_type)
            time.sleep(2)  # Wait for price to update
            
            # Extract current state
            account_data = {
                'business_name': 'Alpha Capital Group',
                'account_size': account_size.replace(',', ''),
                'sale_price': self._extract_current_price(),
                'funded_full_price': self._extract_funded_price_current(),
                'discount_coupon_code': self._extract_current_discount(),
                'trail_type': self._normalize_plan_type(plan_type),
                'trustpilot_score': self._extract_trustpilot_current(),
                'profit_goal': self._extract_profit_target_current(),
                'scraped_at': datetime.now().isoformat()
            }
            
            return account_data
            
        except Exception as e:
            self.logger.warning(f"Error scraping combination {account_size}-{plan_type}: {e}")
            return {}
            
    def _select_account_size(self, size: str):
        """Try to select account size on the page"""
        selectors = [
            f"button:contains('{size}')",
            f"button:contains('${size}')",
            f"[data-value='{size}']",
            f"[value='{size}']"
        ]
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed() and element.is_enabled():
                    self.driver.execute_script("arguments[0].click();", element)
                    return
            except:
                continue
                
    def _select_plan_type(self, plan_type: str):
        """Try to select plan type on the page"""
        selectors = [
            f"button:contains('{plan_type}')",
            f"[data-plan='{plan_type.lower()}']",
            f".step-button:contains('{plan_type}')"
        ]
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed() and element.is_enabled():
                    self.driver.execute_script("arguments[0].click();", element)
                    return
            except:
                continue
                
    def _extract_current_price(self) -> str:
        """Extract currently displayed price"""
        try:
            # Look for price displays
            price_selectors = [
                "[class*='price']:not(:empty)",
                ".assessment-price",
                ".cost",
                ".fee-display"
            ]
            
            for selector in price_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text
                        price_match = re.search(r'\$(\d+(?:\.\d{2})?)', text)
                        if price_match:
                            price = float(price_match.group(1))
                            if 30 <= price <= 2000:  # Reasonable price range
                                return price_match.group(1)
                except:
                    continue
                    
            # Fallback: search page source
            page_text = self.driver.page_source
            price_patterns = [
                r'(?:assessment|price|cost)[:\s]*\$(\d+(?:\.\d{2})?)',
                r'\$(\d+(?:\.\d{2})?)'
            ]
            
            for pattern in price_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for price_str in matches:
                    price = float(price_str)
                    if 30 <= price <= 2000:
                        return price_str
                        
            return ""
            
        except Exception as e:
            self.logger.warning(f"Error extracting current price: {e}")
            return ""
            
    # Keep the existing extraction methods from the original code
    def _extract_account_size(self, text: str) -> str:
        """Extract account size with improved patterns"""
        patterns = [
            r'\$(\d+[,.]?\d*[kK])',  # $100K, $50k, $25K
            r'(\d+[kK])\s*(?:account|challenge|evaluation)',  # 100K account
            r'(\d+,\d{3})\s*(?:account|challenge)',  # 100,000 account
            r'Account.*?(\d+[kK])',  # Account 50K
            r'(\d{2,3}[kK])\s*funded'  # 100K funded
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                size = match.group(1).upper()
                if 'K' in size and ',' not in size:
                    return size
        return ""
        
    def _extract_sale_price(self, text: str) -> str:
        """Extract sale price with improved accuracy"""
        patterns = [
            r'(?:assessment|price|cost|fee).*?\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'(?:£|USD|EUR)\s*(\d+(?:,\d{3})*(?:\.\d{2})?)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for price in matches:
                price_num = float(price.replace(',', ''))
                if 30 <= price_num <= 2000:
                    return price
        return ""
        
    def _extract_funded_price(self, text: str) -> str:
        """Extract funded account price"""
        patterns = [
            r'funded.*?\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'full.*?price.*?\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'regular.*?\$(\d+(?:,\d{3})*(?:\.\d{2})?)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""
        
    def _extract_discount_code(self, text: str) -> str:
        """Extract discount codes and percentages"""
        patterns = [
            r'(?:code|coupon)[:\s]+([A-Z0-9]{3,})',
            r'(?:discount|save)[:\s]+(\d+%)',
            r'use\s+code[:\s]+([A-Z0-9]+)',
            r'(\d+%)\s*(?:off|discount)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""
        
    def _extract_trail_type(self, text: str) -> str:
        """Extract evaluation/trial type"""
        patterns = [
            r'(one[- ]?step|two[- ]?step|three[- ]?step)',
            r'(instant|direct|immediate)',
            r'(evaluation|challenge|assessment)',
            r'leverage[:\s]+(\d+:\d+)',
            r'(phase\s+\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).lower()
        return ""
        
    def _extract_trustpilot_score(self, text: str) -> str:
        """Extract Trustpilot score"""
        patterns = [
            r'trustpilot.*?(\d+\.?\d*)',
            r'rating.*?(\d+\.?\d*)',
            r'score.*?(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*(?:stars?|rating)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                score = float(match.group(1))
                if 1 <= score <= 5:
                    return str(score)
        return ""
        
    def _extract_profit_goal(self, text: str) -> str:
        """Extract profit targets and goals"""
        patterns = [
            r'(?:profit|target|goal).*?(\d+%)',
            r'(\d+%)\s*(?:profit|target)',
            r'reach.*?(\d+%)',
            r'achieve.*?(\d+%)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                percentage = int(match.group(1).replace('%', ''))
                if 1 <= percentage <= 50:
                    return match.group(1)
        return ""
        
    # Helper methods for current state extraction
    def _extract_funded_price_current(self) -> str:
        """Extract funded price from current page state"""
        try:
            page_text = self.driver.page_source
            return self._extract_funded_price(page_text)
        except:
            return ""
            
    def _extract_current_discount(self) -> str:
        """Extract discount from current page state"""
        try:
            page_text = self.driver.page_source
            return self._extract_discount_code(page_text)
        except:
            return ""
            
    def _extract_trustpilot_current(self) -> str:
        """Extract Trustpilot score from current page state"""
        try:
            page_text = self.driver.page_source
            return self._extract_trustpilot_score(page_text)
        except:
            return ""
            
    def _extract_profit_target_current(self) -> str:
        """Extract profit target from current page state"""
        try:
            page_text = self.driver.page_source
            return self._extract_profit_goal(page_text)
        except:
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
        """Check if scraped data is valid"""
        required_fields = ['account_size', 'sale_price']
        return any(data.get(field) and str(data.get(field)).strip() for field in required_fields)
        
    def parse_page_source(self, page_source: str) -> List[Dict[str, str]]:
        """Parse page source for account information (fallback method)"""
        accounts_data = []
        
        try:
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Look for sections containing pricing info
            sections = soup.find_all(['div', 'section'], 
                                   class_=re.compile(r'(?:plan|price|account|tier)', re.I))
            
            for section in sections:
                text = section.get_text()
                if len(text.strip()) < 50:
                    continue
                    
                account_data = self.extract_account_info(text)
                
                if account_data and self._is_valid_data(account_data):
                    accounts_data.append(account_data)
                    
            return accounts_data[:10]  # Limit results
            
        except Exception as e:
            self.logger.error(f"Error parsing page source: {e}")
            return []
