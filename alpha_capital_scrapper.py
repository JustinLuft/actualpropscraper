import re
from bs4 import BeautifulSoup
from typing import Dict, List
from datetime import datetime
from .base_scraper import BaseScraper

class AlphaCapitalScraper(BaseScraper):
    """Enhanced scraper for Alpha Capital Group website"""
    
    def get_base_url(self) -> str:
        return "https://alphacapitalgroup.uk/"
        
    def get_selectors(self) -> Dict[str, List[str]]:
        return {
            "primary_selectors": [
                ".account-card",
                ".trading-account", 
                ".plan-card",
                ".evaluation-card",
                "[data-testid*='account']",
                ".pricing-tier",
                ".plan-wrapper"
            ],
            "secondary_selectors": [
                ".card",
                ".package", 
                ".tier",
                ".pricing-card",
                ".plan-item",
                ".product-card"
            ],
            "generic_containers": [
                ".container .row > div",
                ".section .col-md-4",
                ".plans-section > div",
                ".pricing-section > div"
            ]
        }
        
    def extract_account_info(self, element) -> Dict[str, str]:
        """Enhanced extraction with better pattern matching"""
        try:
            # Get both text and HTML content
            text = element.text.strip()
            html = element.get_attribute('outerHTML')
            
            if not text and not html:
                return {}
                
            # Combine text and HTML for better extraction
            combined_content = f"{text}\n{html}"
            
            account_data = {
                'business_name': 'Alpha Capital Group',
                'account_size': self._extract_account_size(combined_content),
                'sale_price': self._extract_sale_price(combined_content),
                'funded_full_price': self._extract_funded_price(combined_content),
                'discount_coupon_code': self._extract_discount_code(combined_content),
                'trail_type': self._extract_trail_type(combined_content),
                'trustpilot_score': self._extract_trustpilot_score(combined_content),
                'profit_goal': self._extract_profit_goal(combined_content),
                'scraped_at': datetime.now().isoformat()
            }
            
            return account_data
            
        except Exception as e:
            self.logger.error(f"Error extracting account info: {e}")
            return {}
            
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
                # Normalize format
                if 'K' in size and ',' not in size:
                    return size
        return ""
        
    def _extract_sale_price(self, text: str) -> str:
        """Extract sale price with improved accuracy"""
        patterns = [
            r'(?:sale|price|cost|fee).*?\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)',  # Any dollar amount
            r'(?:£|USD|EUR)\s*(\d+(?:,\d{3})*(?:\.\d{2})?)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Return the first reasonable price (not too high or low)
                for price in matches:
                    price_num = float(price.replace(',', ''))
                    if 50 <= price_num <= 5000:  # Reasonable price range
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
                if 1 <= score <= 5:  # Valid rating range
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
                if 1 <= percentage <= 50:  # Reasonable profit goal range
                    return match.group(1)
        return ""
        
    def parse_page_source(self, page_source: str) -> List[Dict[str, str]]:
        """Enhanced page source parsing with BeautifulSoup"""
        accounts_data = []
        
        try:
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Look for pricing/account sections
            sections = soup.find_all(['div', 'section'], class_=re.compile(r'(?:plan|price|account|tier)', re.I))
            
            for section in sections:
                text = section.get_text()
                if len(text.strip()) < 50:  # Skip small sections
                    continue
                    
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
                
                # Only add if we found some meaningful data
                if any(v for k, v in account_data.items() if k not in ['business_name', 'scraped_at'] and v):
                    accounts_data.append(account_data)
                    
            # Limit results to avoid duplicates
            return accounts_data[:10]
            
        except Exception as e:
            self.logger.error(f"Error parsing page source: {e}")
            return []
