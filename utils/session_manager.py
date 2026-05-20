"""
Selenium WebDriver session management.
Handles browser initialization, cleanup, and request delays.
"""
import time
import random
import os
import shutil
import stat
import psutil
import subprocess
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
import undetected_chromedriver as uc
from webdriver_manager.firefox import GeckoDriverManager
from typing import Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
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
        self.driver_process_id = None

    def initialize_driver(self) -> WebDriver:
        """
        Initialize and return Selenium WebDriver.
        
        IMPORTANT: This method is stateless - safe to call multiple times.
        Each call creates fresh ChromeOptions. Any previous failed attempt
        is cleaned up automatically.

        Returns:
            Initialized WebDriver instance

        Raises:
            NetworkError: If driver initialization fails
        """
        try:
            if Config.BROWSER_TYPE == "chrome":
                # Always create fresh ChromeOptions (DO NOT REUSE)
                options = uc.ChromeOptions()
                
                if Config.HEADLESS_MODE:
                    options.add_argument("--headless=new")
                
                # Core stability args
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--disable-software-rasterizer")
                options.add_argument("--disable-xss-auditor")
                options.add_argument("--no-first-run")
                options.add_argument("--no-default-browser-check")
                options.add_argument("--disable-sync")
                
                # Headless server stability (prevent zombie processes)
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-plugins")
                options.add_argument("--disable-default-apps")
                options.add_argument("--disable-preconnect")
                options.add_argument("--no-service-autorun")
                options.add_argument("--disable-crash-reporter")
                options.add_argument("--disable-background-networking")
                options.add_argument("--disable-client-side-phishing-detection")
                options.add_argument("--disable-component-extensions-with-background-pages")
                options.add_argument("--disable-default-apps")
                options.add_argument("--disable-hang-monitor")
                options.add_argument("--disable-popup-blocking")
                options.add_argument("--disable-prompt-on-repost")
                options.add_argument("--disable-reading-from-canvas")
                options.add_argument("--disable-renderer-backgrounding")
                options.add_argument("--disable-device-discovery-notifications")
                
                # Performance & resource management
                options.add_argument("--enable-automation")
                options.add_argument("--disable-background-timer-throttling")
                options.add_argument("--disable-renderer-backgrounding")
                options.add_argument("--disable-backgrounding-occluded-windows")
                options.add_argument("--disable-breakpad")
                options.add_argument("--disable-client-side-phishing-detection")
                options.add_argument("--disable-component-extensions")
                options.add_argument("--disable-component-update")
                
                options.add_argument("--window-size=1920,1080")
                options.add_argument(f"user-agent={Config.USER_AGENT}")
                
                logger.info("Initializing undetected ChromeDriver with headless mode")
                try:
                    self.driver = uc.Chrome(options=options, version_main=None)
                except Exception as e:
                    logger.warning(f"First attempt failed: {str(e)}, retrying without version_main")
                    # Create fresh options object - DO NOT REUSE
                    options = uc.ChromeOptions()
                    if Config.HEADLESS_MODE:
                        options.add_argument("--headless=new")
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-dev-shm-usage")
                    options.add_argument("--disable-gpu")
                    options.add_argument("--disable-software-rasterizer")
                    options.add_argument("--disable-xss-auditor")
                    options.add_argument("--no-first-run")
                    options.add_argument("--no-default-browser-check")
                    options.add_argument("--disable-sync")
                    options.add_argument("--disable-extensions")
                    options.add_argument("--disable-plugins")
                    options.add_argument("--disable-default-apps")
                    options.add_argument("--disable-preconnect")
                    options.add_argument("--no-service-autorun")
                    options.add_argument("--disable-crash-reporter")
                    options.add_argument("--disable-background-networking")
                    options.add_argument("--disable-client-side-phishing-detection")
                    options.add_argument("--disable-component-extensions-with-background-pages")
                    options.add_argument("--disable-hang-monitor")
                    options.add_argument("--disable-popup-blocking")
                    options.add_argument("--disable-prompt-on-repost")
                    options.add_argument("--disable-reading-from-canvas")
                    options.add_argument("--disable-renderer-backgrounding")
                    options.add_argument("--disable-device-discovery-notifications")
                    options.add_argument("--enable-automation")
                    options.add_argument("--disable-background-timer-throttling")
                    options.add_argument("--disable-backgrounding-occluded-windows")
                    options.add_argument("--disable-breakpad")
                    options.add_argument("--disable-component-extensions")
                    options.add_argument("--disable-component-update")
                    options.add_argument("--window-size=1920,1080")
                    options.add_argument(f"user-agent={Config.USER_AGENT}")
                    
                    self.driver = uc.Chrome(options=options)
                
                # Capture driver process ID for cleanup tracking
                try:
                    self.driver_process_id = self.driver.service.process.pid
                    logger.info(f"Chrome process ID: {self.driver_process_id}")
                except Exception:
                    pass

            elif Config.BROWSER_TYPE == "firefox":
                options = FirefoxOptions()
                if Config.HEADLESS_MODE:
                    options.add_argument("--headless")
                options.add_argument(f"user-agent={Config.USER_AGENT}")
                
                geckodriver_path = shutil.which("geckodriver")
                if geckodriver_path:
                    logger.info(f"Using system GeckoDriver: {geckodriver_path}")
                    service = FirefoxService(geckodriver_path)
                else:
                    logger.info("System GeckoDriver not found, using webdriver-manager")
                    driver_path = GeckoDriverManager().install()
                    os.chmod(driver_path, stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
                    service = FirefoxService(driver_path)
                
                self.driver = webdriver.Firefox(service=service, options=options)
                
                # Capture driver process ID for cleanup tracking
                try:
                    self.driver_process_id = self.driver.service.process.pid
                    logger.info(f"Firefox process ID: {self.driver_process_id}")
                except Exception:
                    pass

            else:
                raise ValueError(f"Unsupported browser type: {Config.BROWSER_TYPE}")

            # Set implicit wait
            self.driver.implicitly_wait(Config.REQUEST_TIMEOUT)
            self.wait = WebDriverWait(self.driver, Config.REQUEST_TIMEOUT)

            logger.info(f"WebDriver initialized successfully ({Config.BROWSER_TYPE})")
            return self.driver

        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {str(e)}")
            logger.error("If running on headless server, try: sudo apt-get install -y xvfb libxrender1 libxrandr2")
            
            # Force cleanup any lingering processes before raising
            try:
                self._force_cleanup_processes()
            except Exception as cleanup_error:
                logger.debug(f"Cleanup during exception: {cleanup_error}")
            
            raise NetworkError(f"WebDriver initialization failed: {str(e)}")

    def quit_driver(self) -> None:
        """
        Close and quit the WebDriver with aggressive cleanup for headless servers.
        Handles stuck processes and ensures full resource release.
        """
        if not self.driver:
            return
        
        try:
            # Step 1: Graceful quit with timeout
            logger.info("Closing WebDriver connections...")
            self.driver.quit()
            time.sleep(0.5)
            logger.info("WebDriver quit successfully")
            
        except Exception as e:
            logger.warning(f"Error during graceful quit: {str(e)}")
        
        finally:
            # Step 2: Force kill lingering processes (zombie cleanup)
            try:
                self._force_cleanup_processes()
            except Exception as cleanup_error:
                logger.error(f"Error during process cleanup: {cleanup_error}")
            
            self.driver = None
            self.wait = None

    def _force_cleanup_processes(self) -> None:
        """
        Force terminate lingering browser processes.
        Essential for headless servers where zombie processes accumulate.
        """
        if not self.driver_process_id:
            return
        
        logger.debug(f"Checking for lingering processes of driver PID {self.driver_process_id}")
        
        try:
            # Try to get parent process
            try:
                parent = psutil.Process(self.driver_process_id)
                # Get all children (Chrome spawns multiple processes)
                children = parent.children(recursive=True)
                
                if parent.is_running():
                    logger.warning(f"Driver process {self.driver_process_id} still running, terminating...")
                    parent.terminate()
                    time.sleep(0.3)
                    
                    if parent.is_running():
                        logger.warning(f"Force killing driver process {self.driver_process_id}")
                        parent.kill()
                
                # Kill any child processes
                for child in children:
                    try:
                        if child.is_running():
                            logger.debug(f"Terminating child process {child.pid}")
                            child.terminate()
                            time.sleep(0.1)
                            if child.is_running():
                                child.kill()
                    except Exception as e:
                        logger.debug(f"Could not kill child process {child.pid}: {e}")
                        
            except psutil.NoSuchProcess:
                logger.debug(f"Driver process {self.driver_process_id} already terminated")
            except Exception as e:
                logger.debug(f"Could not access driver process: {e}")
        
        except Exception as e:
            logger.error(f"Force cleanup failed: {e}")


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
