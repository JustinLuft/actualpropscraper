import os
import sys
from datetime import datetime
from typing import List, Dict
import pandas as pd
from scraper_factory import ScraperFactory
from config import Config

def setup_logging():
    """Setup main logging"""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('scraper.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('MainScraper')

def main():
    """Enhanced main function with better error handling and reporting"""
    
    logger = setup_logging()
    logger.info("Starting web scraper framework...")
    
    try:
        # Load configuration
        config = Config()
        
        # Create output directory
        output_dir = config.get_output_dir()
        os.makedirs(output_dir, exist_ok=True)
        
        # Get websites to scrape
        websites = config.get_websites()
        if not websites:
            logger.error("No websites configured to scrape!")
            logger.info("Please add websites to config.json or set WEBSITES environment variable")
            sys.exit(1)
            
        logger.info(f"Starting scraping process for {len(websites)} websites...")
        logger.info(f"Websites: {', '.join(websites)}")
        
        all_results = []
        successful_scrapes = 0
        failed_scrapes = 0
        
        for website in websites:
            try:
                logger.info(f"\n{'='*50}")
                logger.info(f"Scraping: {website}")
                logger.info(f"{'='*50}")
                
                # Check if website is supported
                if not ScraperFactory.is_supported(website):
                    logger.error(f"No scraper available for {website}")
                    logger.info(f"Available scrapers: {ScraperFactory.get_available_scrapers()}")
                    failed_scrapes += 1
                    continue
                
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
                    clean_website = website.replace('.', '_').replace('/', '_')
                    filename = f"{output_dir}/{clean_website}_{timestamp}.csv"
                    
                    if scraper.save_to_csv(results, filename):
                        all_results.extend(results)
                        successful_scrapes += 1
                        logger.info(f"✅ Successfully scraped {len(results)} records from {website}")
                    else:
                        logger.error(f"❌ Failed to save data from {website}")
                        failed_scrapes += 1
                else:
                    logger.warning(f"❌ No data scraped from {website}")
                    failed_scrapes += 1
                    
            except Exception as e:
                logger.error(f"❌ Error scraping {website}: {e}")
                failed_scrapes += 1
                continue
                
        # Generate final report
        generate_report(all_results, output_dir, successful_scrapes, failed_scrapes, logger)
        
    except Exception as e:
        logger.error(f"Critical error in main process: {e}")
        sys.exit(1)

def generate_report(all_results: List[Dict], output_dir: str, successful: int, failed: int, logger):
    """Generate comprehensive scraping report"""
    
    logger.info(f"\n{'='*60}")
    logger.info("SCRAPING REPORT")
    logger.info(f"{'='*60}")
    
    if all_results:
        # Save combined results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_filename = f"{output_dir}/combined_results_{timestamp}.csv"
        
        try:
            df = pd.DataFrame(all_results)
            df.to_csv(combined_filename, index=False)
            logger.info(f"📊 Combined results saved to: {combined_filename}")
            
            # Generate statistics
            total_records = len(all_results)
            unique_websites = len(set(record.get('business_name', 'Unknown') for record in all_results))
            
            # Price statistics
            prices = []
            for record in all_results:
                price_str = record.get('sale_price', '')
                if price_str:
                    try:
                        # Extract numeric value
                        numeric_part = ''.join(c for c in price_str if c.isdigit() or c == '.')
                        if numeric_part:
                            prices.append(float(numeric_part))
                    except (ValueError, TypeError):
                        continue
            
            logger.info(f"📈 Total records scraped: {total_records}")
            logger.info(f"🏢 Unique businesses: {unique_websites}")
            logger.info(f"✅ Successful scrapes: {successful}")
            logger.info(f"❌ Failed scrapes: {failed}")
            
            if prices:
                logger.info(f"💰 Price range: ${min(prices):.2f} - ${max(prices):.2f}")
                logger.info(f"💰 Average price: ${sum(prices)/len(prices):.2f}")
            
            # Business breakdown
            business_counts = {}
            for record in all_results:
                business = record.get('business_name', 'Unknown')
                business_counts[business] = business_counts.get(business, 0) + 1
                
            logger.info(f"\n📋 Records per business:")
            for business, count in business_counts.items():
                logger.info(f"   {business}: {count} records")
                
        except Exception as e:
            logger.error(f"Error generating combined report: {e}")
    else:
        logger.warning("❌ No data was successfully scraped from any website")
        
    logger.info(f"\n{'='*60}")
    logger.info("SCRAPING COMPLETED")
    logger.info(f"{'='*60}")

if __name__ == "__main__":
    main()
