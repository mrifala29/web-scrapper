"""
Website authentication handler.
Handles login and session management.
"""
from selenium.webdriver.common.by import By
import time
from config.config import Config
from utils.logging_setup import logger
from utils.exceptions import LoginFailedError
from utils.session_manager import SessionManager


class LoginHandler:
    """Handle authentication to the target website."""

    def __init__(self, session_manager: SessionManager):
        """
        Initialize login handler.

        Args:
            session_manager: SessionManager instance
        """
        self.session_manager = session_manager
        self.driver = session_manager.driver
        self.is_logged_in = False

    def login(self) -> bool:
        """
        Perform login to the website.

        Returns:
            True if login successful, False otherwise

        Raises:
            LoginFailedError: If login fails after max retries
        """
        for attempt in range(Config.MAX_RETRIES):
            try:
                logger.info(
                    f"Attempting login (attempt {attempt + 1}/{Config.MAX_RETRIES})"
                )

                # Navigate to login URL
                self.driver.get(Config.LOGIN_URL)
                logger.debug(f"Navigated to: {Config.LOGIN_URL}")

                # Apply request delay
                SessionManager.apply_request_delay()

                # TODO: Update these selectors based on actual website structure
                # These are placeholder selectors - you need to inspect the website
                # and replace them with actual CSS selectors or XPath

                # CSS selectors from website HTML inspection
                # MSISDN field: <input id="username" name="username" ...>
                # Password field: <input id="password" name="password" ...>
                # Login button: <input type="button" name="sub" id="sub" ...>
                msisdn_field_selector = "#username"
                password_field_selector = "#password"
                login_button_selector = "#sub"

                self.session_manager.wait_for_element(By.CSS_SELECTOR, msisdn_field_selector)
                msisdn_field = self.driver.find_element(By.CSS_SELECTOR, msisdn_field_selector)
                msisdn_field.clear()
                msisdn_field.send_keys(Config.WEBSITE_MSISDN)
                logger.debug("MSISDN field filled")

                # Fill password field
                password_field = self.driver.find_element(By.CSS_SELECTOR, password_field_selector)
                password_field.clear()
                password_field.send_keys(Config.WEBSITE_PASSWORD)
                logger.debug("Password field filled")

                # Click login button
                login_button = self.driver.find_element(By.CSS_SELECTOR, login_button_selector)
                login_button.click()
                logger.info("Login button clicked")

                # Wait for page to load after login
                time.sleep(3)

                # Check if login was successful
                # TODO: Update this verification based on website behavior
                # This could be checking for a specific element, URL change, etc.
                if self._verify_login():
                    logger.info("Login successful!")
                    self.is_logged_in = True
                    return True
                else:
                    logger.warning(f"Login verification failed (attempt {attempt + 1})")

            except Exception as e:
                logger.error(f"Login error on attempt {attempt + 1}: {str(e)}")
                if attempt < Config.MAX_RETRIES - 1:
                    wait_time = Config.RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

        raise LoginFailedError(
            f"Login failed after {Config.MAX_RETRIES} attempts. "
            "Check credentials and website selectors in auth_handler.py"
        )

    def _verify_login(self) -> bool:
        """
        Verify that login was successful.

        Returns:
            True if login verified, False otherwise
        """
        try:
            # TODO: Implement actual verification logic
            # Common approaches:
            # 1. Check if URL changed from login page
            # 2. Check if specific element exists (e.g., user profile, logout button)
            # 3. Check for error message absence
            # 4. Check for specific text/content

            current_url = self.driver.current_url
            logger.debug(f"Current URL after login attempt: {current_url}")

            # Placeholder verification - replace with actual logic
            if "login" not in current_url.lower():
                logger.debug("URL verification passed - not on login page")
                return True

            return False

        except Exception as e:
            logger.error(f"Login verification error: {str(e)}")
            return False

    def logout(self) -> None:
        """
        Logout from the website if needed.
        """
        try:
            # TODO: Implement logout logic if needed
            logger.info("Logout completed")
            self.is_logged_in = False
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")
