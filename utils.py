import os
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
import logging

def setup_logging(log_file: str = 'scraper.log') -> logging.Logger:
    """Setup enhanced logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('ScraperUtils')

def clean_text(text: str) -> str:
    """Clean and normalize text data"""
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    cleaned = ' '.join(text.split())
    # Remove special characters that might cause CSV issues
    cleaned = cleaned.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    return cleaned.strip()

def validate_price(price_str: str) -> bool:
    """Validate if price string is reasonable"""
    if not price_str:
        return False
    
    try:
        # Extract numeric value
        numeric_part = ''.join(c for c in price_str if c.isdigit() or c == '.')
        if not numeric_part:
            return False
        
        price = float(numeric_part)
        # Check if price is in reasonable range
        return 10 <= price <= 10000
    except (ValueError, TypeError):
        return False

def merge_csv_files(file_paths: List[str], output_file: str) -> bool:
    """Merge multiple CSV files into one"""
    logger = setup_logging()
    
    try:
        all_data = []
        for file_path in file_paths:
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                all_data.append(df)
                logger.info(f"Loaded {len(df)} records from {file_path}")
            else:
                logger.warning(f"File not found: {file_path}")
        
        if all_data:
            merged_df = pd.concat(all_data, ignore_index=True)
            # Remove duplicates
            merged_df = merged_df.drop_duplicates()
            merged_df.to_csv(output_file, index=False)
            logger.info(f"Merged {len(merged_df)} records to {output_file}")
            return True
        else:
            logger.error("No data to merge")
            return False
            
    except Exception as e:
        logger.error(f"Error merging CSV files: {e}")
        return False

def generate_summary_report(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate summary statistics from scraped data"""
    if not data:
        return {"error": "No data provided"}
    
    total_records = len(data)
    
    # Count by business
    business_counts = {}
    prices = []
    account_sizes = []
    
    for record in data:
        business = record.get('business_name', 'Unknown')
        business_counts[business] = business_counts.get(business, 0) + 1
        
        # Extract price data
        sale_price = record.get('sale_price', '')
        if validate_price(sale_price):
            numeric_price = float(''.join(c for c in sale_price if c.isdigit() or c == '.'))
            prices.append(numeric_price)
        
        # Extract account size data
        account_size = record.get('account_size', '')
        if account_size and account_size.replace(',', '').isdigit():
            account_sizes.append(int(account_size.replace(',', '')))
    
    # Calculate statistics
    price_stats = {}
    if prices:
        price_stats = {
            'avg_price': round(sum(prices) / len(prices), 2),
            'min_price': min(prices),
            'max_price': max(prices),
            'total_listings_with_price': len(prices)
        }
    
    account_stats = {}
    if account_sizes:
        account_stats = {
            'avg_account_size': round(sum(account_sizes) / len(account_sizes), 0),
            'min_account_size': min(account_sizes),
            'max_account_size': max(account_sizes),
            'total_with_account_data': len(account_sizes)
        }
    
    return {
        'generated_at': datetime.now().isoformat(),
        'total_records': total_records,
        'business_breakdown': business_counts,
        'price_statistics': price_stats,
        'account_statistics': account_stats,
        'data_quality': {
            'records_with_valid_prices': len(prices),
            'records_with_account_data': len(account_sizes),
            'price_validation_rate': round(len(prices) / total_records * 100, 2) if total_records > 0 else 0
        }
    }

def save_to_csv(data: List[Dict[str, Any]], filename: str, include_timestamp: bool = True) -> bool:
    """Save scraped data to CSV file with optional timestamp"""
    logger = setup_logging()
    
    try:
        if not data:
            logger.error("No data to save")
            return False
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Clean text columns
        text_columns = df.select_dtypes(include=['object']).columns
        for col in text_columns:
            df[col] = df[col].astype(str).apply(clean_text)
        
        # Add timestamp if requested
        if include_timestamp:
            df['scraped_at'] = datetime.now().isoformat()
        
        # Generate filename with timestamp if not provided
        if include_timestamp and not filename.endswith('.csv'):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{filename}_{timestamp}.csv"
        elif not filename.endswith('.csv'):
            filename = f"{filename}.csv"
        
        # Save to CSV
        df.to_csv(filename, index=False, encoding='utf-8')
        logger.info(f"Saved {len(df)} records to {filename}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving to CSV: {e}")
        return False

def filter_valid_records(data: List[Dict[str, Any]], required_fields: List[str] = None) -> List[Dict[str, Any]]:
    """Filter out records that don't meet validation criteria"""
    if required_fields is None:
        required_fields = ['business_name', 'sale_price']
    
    valid_records = []
    
    for record in data:
        is_valid = True
        
        # Check required fields
        for field in required_fields:
            if not record.get(field):
                is_valid = False
                break
        
        # Validate price if present
        if 'sale_price' in record and not validate_price(record['sale_price']):
            is_valid = False
        
        if is_valid:
            valid_records.append(record)
    
    return valid_records

def create_backup(filename: str) -> bool:
    """Create a backup of existing file before overwriting"""
    if os.path.exists(filename):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{filename}.backup_{timestamp}"
        try:
            os.rename(filename, backup_name)
            return True
        except Exception as e:
            logging.error(f"Failed to create backup: {e}")
            return False
    return True
