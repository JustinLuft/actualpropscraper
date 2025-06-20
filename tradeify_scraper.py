import requests
from bs4 import BeautifulSoup
import re
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def TradeifyScraper(driver):
    """
    Scrape Tradeify plans data
    Expects a selenium webdriver instance to be passed in
    """
    try:
        # Navigate to Tradeify
        driver.get("https://tradeify.com")
        time.sleep(5)
        
        plans_data = []
        
        # Look for plan cards - try multiple selectors
        selectors_to_try = [
            "div[class*='plan']",
            "div[class*='card']", 
            "div[class*='account']",
            ".pricing-card",
            "div[class*='pricing']"
        ]
        
        plan_elements = []
        for selector in selectors_to_try:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements and len(elements) >= 3:  # Expect at least 3-4 plans
                    plan_elements = elements
                    break
            except:
                continue
        
        if not plan_elements:
            # Fallback: get all divs and filter by content
            all_divs = driver.find_elements(By.TAG_NAME, "div")
            plan_elements = []
            for div in all_divs:
                text = div.text.lower()
                if any(keyword in text for keyword in ['25k', '50k', '100k', '150k']) and '$' in text:
                    plan_elements.append(div)
        
        # Extract data from each plan
        for i, element in enumerate(plan_elements[:4]):  # Limit to 4 plans max
            try:
                plan_data = extract_plan_data(element)
                if plan_data:
                    plans_data.append(plan_data)
            except Exception as e:
                print(f"Error extracting plan {i+1}: {e}")
                continue
        
        # Get Trustpilot score
        trustpilot_score = get_trustpilot_score(driver)
        
        # Add common data to all plans
        for plan in plans_data:
            plan['business_name'] = 'Tradeify'
            plan['trustpilot_score'] = trustpilot_score
            plan['funded_full_price'] = None  # Not typically shown
            plan['discount_coupon_code'] = None  # Would need to check for active promos
        
        return plans_data
        
    except Exception as e:
        print(f"Error scraping Tradeify: {e}")
        return []

def extract_plan_data(element):
    """Extract data from a single plan element"""
    try:
        plan_data = {
            'business_name': 'Tradeify',
            'account_size': None,
            'sale_price': None,
            'funded_full_price': None,
            'discount_coupon_code': None,
            'trial_type': None,
            'trustpilot_score': None,
            'profit_goal': None
        }
        
        text = element.text
        
        # Extract account size
        size_match = re.search(r'\$?(\d+)k\s*account', text, re.IGNORECASE)
        if size_match:
            plan_data['account_size'] = f"{size_match.group(1)}k"
        
        # Extract sale price
        price_match = re.search(r'\$(\d{3,4})\s*one time fee', text, re.IGNORECASE)
        if not price_match:
            price_match = re.search(r'\$(\d{3,4})', text)
        if price_match:
            plan_data['sale_price'] = f"${price_match.group(1)}"
        
        # Extract trial type
        if 'straight to sim funded' in text.lower():
            plan_data['trial_type'] = 'Straight to Sim Funded'
        elif 'advanced' in text.lower():
            plan_data['trial_type'] = 'Advanced'
        elif 'growth' in text.lower():
            plan_data['trial_type'] = 'Growth'
        
        # Extract profit goal (usually a percentage)
        profit_match = re.search(r'(\d+)%.*profit', text, re.IGNORECASE)
        if profit_match:
            plan_data['profit_goal'] = f"{profit_match.group(1)}%"
        
        return plan_data if plan_data['account_size'] else None
        
    except Exception as e:
        print(f"Error extracting plan data: {e}")
        return None

def get_trustpilot_score(driver):
    """Get Trustpilot score for Tradeify"""
    try:
        current_url = driver.current_url
        driver.get("https://www.trustpilot.com/review/tradeify.com")
        time.sleep(3)
        
        # Look for rating
        rating_selectors = [
            "[data-service-review-rating]",
            ".star-rating",
            "[class*='rating']",
            ".trustscore-rating"
        ]
        
        for selector in rating_selectors:
            try:
                rating_element = driver.find_element(By.CSS_SELECTOR, selector)
                if rating_element:
                    rating_text = rating_element.get_attribute("data-service-review-rating") or \
                                 rating_element.get_attribute("aria-label") or \
                                 rating_element.text
                    
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        score = float(rating_match.group(1))
                        driver.get(current_url)  # Go back to original page
                        return score
            except:
                continue
        
        driver.get(current_url)  # Go back to original page
        return None
        
    except Exception as e:
        print(f"Could not get Trustpilot score: {e}")
        return None

# Usage in your existing framework:
# from tradeify_scraper import scrape_tradeify
# data = scrape_tradeify(your_driver_instance)
