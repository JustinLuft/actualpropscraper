import os
import json
from typing import Dict, List, Any

class Config:
    """Enhanced configuration management"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file and environment variables"""
        # Default configuration
        config = {
            "websites": [],
            "output_dir": "output",
            "headless": True,
            "timeout": 30,
            "max_retries": 3,
            "delay_between_requests": 2,
            "user_agents": [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            ]
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
        env_mappings = {
            "HEADLESS": ("headless", lambda x: x.lower() == "true"),
            "TIMEOUT": ("timeout", int),
            "OUTPUT_DIR": ("output_dir", str),
            "MAX_RETRIES": ("max_retries", int),
            "DELAY_BETWEEN_REQUESTS": ("delay_between_requests", float)
        }
        
        for env_var, (config_key, converter) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    config[config_key] = converter(value)
                except (ValueError, TypeError) as e:
                    print(f"Error converting {env_var}: {e}")
        
        # Load websites from environment variable
        websites_env = os.getenv("WEBSITES")
        if websites_env:
            config["websites"] = [w.strip() for w in websites_env.split(",") if w.strip()]
            
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
        return self.config.get("timeout", 30)
        
    def get_max_retries(self) -> int:
        """Get maximum number of retries"""
        return self.config.get("max_retries", 3)
        
    def get_delay(self) -> float:
        """Get delay between requests"""
        return self.config.get("delay_between_requests", 2)
        
    def get_user_agents(self) -> List[str]:
        """Get list of user agents"""
        return self.config.get("user_agents", [])
