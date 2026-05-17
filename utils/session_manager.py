"""
Selenium WebDriver session management.
Handles browser initialization, cleanup, and request delays.
"""
import time
import random
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from typing import Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from config.config import Config
from utils.logging_setup import logger
from utils.exceptions import NetworkError


class SessionManager:
    """Manage Selenium WebDriver lifecycle and request behavior."""

    def __init__(self):
        """Initialize session manager."""
        self.driver = None
        self.wait = None

    def initialize_driver(self) -> WebDriver:
        """
        Initialize and return Selenium WebDriver.

        Returns:
            Initialized WebDriver instance

        Raises:
            NetworkError: If driver initialization fails
        """
        try:
            if Config.BROWSER_TYPE == "chrome":
                options = ChromeOptions()
                if Config.HEADLESS_MODE:
                    options.add_argument("--headless=new")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-setuid-sandbox")
                options.add_argument("--single-process")
                options.add_argument("--window-size=1920,1080")
                options.add_argument(f"user-agent={Config.USER_AGENT}")
                self.driver = webdriver.Chrome(options=options)

            elif Config.BROWSER_TYPE == "firefox":
                options = FirefoxOptions()
                if Config.HEADLESS_MODE:
                    options.add_argument("--headless")
                options.add_argument(f"user-agent={Config.USER_AGENT}")
                self.driver = webdriver.Firefox(options=options)

            else:
                raise ValueError(f"Unsupported browser type: {Config.BROWSER_TYPE}")

            # Set implicit wait
            self.driver.implicitly_wait(Config.REQUEST_TIMEOUT)
            self.wait = WebDriverWait(self.driver, Config.REQUEST_TIMEOUT)

            logger.info(f"WebDriver initialized successfully ({Config.BROWSER_TYPE})")
            return self.driver

        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise NetworkError(f"WebDriver initialization failed: {str(e)}")

    def quit_driver(self) -> None:
        """Close and quit the WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver quit successfully")
            except Exception as e:
                logger.error(f"Error quitting WebDriver: {str(e)}")

    @staticmethod
    def apply_request_delay() -> None:
        """Apply random delay between requests to avoid rate limiting."""
        delay = random.uniform(Config.MIN_REQUEST_DELAY, Config.MAX_REQUEST_DELAY)
        logger.debug(f"Applying request delay: {delay:.2f} seconds")
        time.sleep(delay)

    def wait_for_element(self, by: By, value: str, timeout: Optional[int] = None) -> None:
        """
        Wait for element to be present in DOM.

        Args:
            by: Selenium By locator type
            value: Locator value
            timeout: Custom timeout in seconds

        Raises:
            NetworkError: If element is not found within timeout
        """
        if timeout is None:
            timeout = Config.REQUEST_TIMEOUT

        try:
            self.wait.until(
                EC.presence_of_element_located((by, value))
            )
            logger.debug(f"Element found: {by}={value}")
        except Exception as e:
            logger.error(f"Element not found: {by}={value} - {str(e)}")
            raise NetworkError(f"Element not found: {str(e)}")

    def get_page_source(self) -> str:
        """
        Get current page source.

        Returns:
            Page HTML source
        """
        return self.driver.page_source
