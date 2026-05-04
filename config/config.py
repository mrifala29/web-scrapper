"""
Configuration management for web scraper.
Loads configuration from environment variables with validation.
"""
import os
from dotenv import load_dotenv
from typing import Optional

# Load .env file
load_dotenv()


class Config:
    """Configuration class for web scraper settings."""

    # Credentials
    WEBSITE_MSISDN: str = os.getenv("WEBSITE_MSISDN", "")
    WEBSITE_PASSWORD: str = os.getenv("WEBSITE_PASSWORD", "")

    # URLs
    BASE_URL: str = os.getenv(
        "BASE_URL", "https://xg.smshj.com"
    )
    LOGIN_URL: str = os.getenv(
        "LOGIN_URL", "https://xg.smshj.com/hbshengma/operator/deliverydetail.html"
    )
    REPORT_URL: str = os.getenv(
        "REPORT_URL", "https://xg.smshj.com/hbshengma/operator/deliverydetail.html"
    )

    # Scraper Settings
    SCRAPE_INTERVAL: int = int(os.getenv("SCRAPE_INTERVAL", "86400"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: int = int(os.getenv("RETRY_DELAY", "5"))

    # Rate Limiting
    MIN_REQUEST_DELAY: float = float(os.getenv("MIN_REQUEST_DELAY", "1"))
    MAX_REQUEST_DELAY: float = float(os.getenv("MAX_REQUEST_DELAY", "3"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/scraper.log")

    # Browser Settings
    BROWSER_TYPE: str = os.getenv("BROWSER_TYPE", "chrome").lower()
    HEADLESS_MODE: bool = os.getenv("HEADLESS_MODE", "true").lower() == "true"
    USER_AGENT: str = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    )

    # Data Settings
    OUTPUT_FORMAT: str = os.getenv("OUTPUT_FORMAT", "json")
    DATA_FOLDER: str = os.getenv("DATA_FOLDER", "data")
    KEEP_BACKUPS: int = int(os.getenv("KEEP_BACKUPS", "10"))

    # Scheduling
    SCHEDULE_TIME: str = os.getenv("SCHEDULE_TIME", "02:00")
    SCHEDULE_TIMEZONE: str = os.getenv("SCHEDULE_TIMEZONE", "UTC")

    @classmethod
    def validate(cls) -> bool:
        """Validate critical configuration values."""
        if not cls.WEBSITE_MSISDN:
            raise ValueError("WEBSITE_MSISDN is not set in .env file")
        if not cls.WEBSITE_PASSWORD:
            raise ValueError("WEBSITE_PASSWORD is not set in .env file")
        return True

    @classmethod
    def get_all(cls) -> dict:
        """Get all configuration as dictionary (for logging)."""
        return {
            k: v
            for k, v in cls.__dict__.items()
            if not k.startswith("_") and k.isupper()
        }
