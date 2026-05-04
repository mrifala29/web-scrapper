"""
Scheduled jobs for web scraper.
Define and manage recurring scraping tasks.
"""
from datetime import datetime, timezone
from config.config import Config
from utils.logging_setup import logger
from utils.exceptions import ScraperException


def scraping_job() -> None:
    """
    Main scraping job to be executed on schedule.
    Workflow: Initialize → Login → Navigate URLs → Parse → Save → Cleanup
    """
    from scrapers.auth_handler import LoginHandler
    from utils.session_manager import SessionManager
    from scrapers.parser import DataExtractor
    from storage.json_storage import JSONStorage
    from models.sales_data import ScrapingReport
    import time

    session_manager = None
    start_time = datetime.now(timezone.utc)
    all_data = []
    errors = []

    try:
        logger.info("=" * 60)
        logger.info("Starting scheduled scraping job")
        logger.info(f"Job started at: {start_time.isoformat()}")

        # Step 1: Initialize session manager and login
        logger.info("Step 1: Initializing WebDriver session")
        session_manager = SessionManager()
        session_manager.initialize_driver()
        logger.info("WebDriver initialized")

        logger.info("Step 2: Authenticating to website")
        login_handler = LoginHandler(session_manager)
        if not login_handler.login():
            raise ScraperException("Login failed - check credentials in .env")
        logger.info("Authentication successful")

        # Step 2: Build target URLs from config
        logger.info("Step 3: Scraping data from all pages")
        target_urls = {
            name: f"{Config.BASE_URL}{url}" for name, url in Config.get_target_urls().items()
        }

        # Step 3: Extract data from all pages
        logger.info(f"Extracting data from {len(target_urls)} pages")
        start_date = Config.get_start_date()
        end_date = Config.get_end_date()
        logger.info(f"Date range: {start_date.date()} to {end_date.date()}")
        all_data = DataExtractor.extract_all_pages(
            session_manager.driver, 
            target_urls,
            start_date=start_date,
            end_date=end_date,
        )
        logger.info(f"Extracted data from {len(all_data)} pages")

        # Step 4: Build and save report
        logger.info("Step 4: Saving data to JSON")
        end_time = datetime.now(timezone.utc)
        execution_time = (end_time - start_time).total_seconds()

        total_records = sum(len(data.records) for data in all_data)
        total_errors = sum(len(data.errors) for data in all_data)

        report = ScrapingReport(
            run_timestamp=start_time,
            status="success" if total_errors == 0 else "partial",
            total_records_scraped=total_records,
            data_by_submenu={data.submenu: data for data in all_data},
            errors=[],
            execution_time_seconds=execution_time,
        )

        storage = JSONStorage()
        
        # Save in primary format (JSON)
        filename = storage.save_data(report.model_dump(), "scraping_report")
        logger.info(f"Report saved to: {filename}")

        # Save in additional formats based on config
        if Config.OUTPUT_FORMAT == "jsonl" or Config.OUTPUT_FORMAT == "clickhouse":
            from utils.clickhouse_formatter import ClickHouseFormatter
            jsonl_data = ClickHouseFormatter.to_jsonl(all_data)
            
            # Save JSONL file
            import os
            from pathlib import Path
            
            data_dir = Path(Config.DATA_FOLDER)
            data_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
            jsonl_filename = data_dir / f"scraping_data_{timestamp}.jsonl"
            
            with open(jsonl_filename, "w", encoding="utf-8") as f:
                f.write(jsonl_data)
            
            logger.info(f"JSONL data saved to: {jsonl_filename}")

        # Step 5: Cleanup old backups
        logger.info("Step 5: Cleaning up old backup files")
        storage.cleanup_old_files(keep_count=10)
        logger.info("Cleanup completed")

        logger.info("=" * 60)
        logger.info(
            f"Scraping job completed: {total_records} records extracted, "
            f"execution time: {execution_time:.2f}s"
        )
        logger.info("=" * 60)

    except ScraperException as e:
        logger.error(f"Scraping job failed: {str(e)}")
        logger.info("Check .env credentials and website selectors")
    except Exception as e:
        logger.error(f"Unexpected error in scraping job: {str(e)}", exc_info=True)
    finally:
        # Cleanup: Close WebDriver
        if session_manager:
            logger.info("Closing WebDriver session")
            session_manager.quit_driver()
            logger.info("WebDriver closed")


def health_check_job() -> None:
    """
    Health check job to verify system status.
    """
    try:
        logger.debug("Running health check...")
        logger.debug(f"Config validation: {Config.validate()}")
        logger.debug("Health check passed")
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
