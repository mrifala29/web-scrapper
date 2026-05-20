"""
Entry point for machine temperature scraper.
Runs independently from the sales scraper (main.py).

Cron examples (server):
    # Every 6 hours
    0 */6 * * * cd /app && venv/bin/python machine.py --run-once

    # With APScheduler (long-running process)
    python machine.py --schedule
"""
import sys
import time
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler

from config.config import Config
from utils.logging_setup import logger
from utils.exceptions import ScraperException
from utils.retry_handler import RetryHandler, RetryConfig


def _cleanup_session(session_manager_holder: dict) -> None:
    """Quit and remove session_manager from holder (called before each retry)."""
    sm = session_manager_holder.pop("session_manager", None)
    if sm:
        try:
            sm.quit_driver()
        except Exception as e:
            logger.debug(f"Session cleanup error (ignored): {e}")


def _execute_machine_scraping(session_manager_holder: dict) -> None:
    """
    Inner function for machine scraping (retryable).
    Designed to be called by retry handler.
    
    Always creates a FRESH SessionManager per attempt.
    Broken sessions are cleaned up before re-raising to ensure
    next retry starts with a clean state.
    
    Raises:
        Exception: On any scraping error (will be caught by retry handler)
    """
    from scrapers.auth_handler import LoginHandler
    from utils.session_manager import SessionManager
    from scrapers.machine_scraper import MachineTemperatureScraper

    # Always create fresh SessionManager for each attempt
    # Never reuse — a broken driver causes "NoneType has no attribute 'get'"
    logger.info("Step 1: Initializing WebDriver session")
    session_manager = SessionManager()
    session_manager_holder["session_manager"] = session_manager

    try:
        session_manager.initialize_driver()

        # Step 2: Login
        logger.info("Step 2: Authenticating to website")
        login_handler = LoginHandler(session_manager)
        if not login_handler.login():
            raise ScraperException("Login failed - check credentials in .env")
        logger.info("Authentication successful")

        # Step 3: Scrape machines
        logger.info("Step 3: Scraping machine list and temperatures")
        scraper = MachineTemperatureScraper(
            driver=session_manager.driver,
            base_url=Config.BASE_URL,
        )
        result = scraper.scrape_all()
        logger.info(
            f"Machine scraping done: {result.record_count} machines, "
            f"{len(result.errors)} errors"
        )

        if result.errors:
            for err in result.errors:
                logger.warning(f"  - {err}")

        # Step 4: Insert into ClickHouse (if configured)
        if Config.clickhouse_enabled():
            if result.record_count > 0:
                logger.info("Step 4: Inserting into ClickHouse")
                from storage.clickhouse_storage import ClickHouseStorage
                ch = ClickHouseStorage(
                    host=Config.CLICKHOUSE_HOST,
                    port=Config.CLICKHOUSE_PORT,
                    database=Config.CLICKHOUSE_DATABASE,
                    username=Config.CLICKHOUSE_USER,
                    password=Config.CLICKHOUSE_PASSWORD,
                    secure=Config.CLICKHOUSE_SECURE,
                )
                try:
                    ch.connect()
                    inserted = ch.insert_machines(result)
                    logger.info(f"ClickHouse: inserted {inserted} machine rows")
                except Exception as ch_exc:
                    logger.error(f"ClickHouse insert failed: {ch_exc}", exc_info=True)
                    raise ScraperException(f"ClickHouse insert failed: {ch_exc}")
                finally:
                    ch.close()
            else:
                logger.info("Step 4: No records to insert, skipping ClickHouse")
        else:
            logger.info("Step 4: ClickHouse not configured (CLICKHOUSE_HOST empty), skipping")

    except Exception as e:
        # Cleanup broken session before re-raise so next retry starts fresh
        logger.error(f"Scraping error: {e}")
        _cleanup_session(session_manager_holder)
        raise


def machine_job() -> None:
    """
    Standalone machine scraping job with automatic retry.
    Scrapes current machine state and inserts into ClickHouse.
    No date filtering — machine data is always real-time current state.
    
    Uses process locking to prevent concurrent execution when multiple
    schedulers run (e.g., machine job every 30min + main.py at 01:00 UTC).
    
    Uses retry handler to recover from connection timeout or temporary failures:
    - Max 4 attempts total
    - 5 minute delay between retries
    - Retries only on connection/scraping errors
    
    IMPORTANT: Lock is acquired AFTER successful WebDriver initialization.
    This ensures lock is released quickly if initialization fails.
    """
    from utils.process_lock import ProcessLock

    start_time = datetime.now(timezone.utc)
    lock = ProcessLock("machine_scraper")
    session_manager_holder = {}

    try:
        # Acquire lock at start to prevent concurrent execution.
        # Stale lock detection: if previous process died, lock is stolen automatically.
        # Short timeout: if another live instance is running, exit immediately.
        logger.info("Attempting to acquire machine scraper lock (timeout: 5s)...")
        if not lock.acquire(timeout=5):
            logger.warning(
                "Could not acquire machine scraper lock — another live instance is running. "
                "Skipping this run to prevent concurrent execution."
            )
            return

        logger.info("=" * 60)
        logger.info("Machine scraping job started")
        logger.info(f"Run time: {start_time.isoformat()}")

        # Configure retry handler: max 4 attempts, 5 minute delay
        retry_config = RetryConfig(
            max_attempts=4,
            retry_delay_seconds=300,  # 5 minutes
            backoff_multiplier=1.0,   # Fixed delay (no exponential backoff)
            retryable_exceptions=(Exception,),  # Retry on all exceptions
        )
        retry_handler = RetryHandler(retry_config)

        success = retry_handler.execute_with_retry(
            _execute_machine_scraping,
            "machine_scraper",
            session_manager_holder,
        )

        if not success:
            logger.error("Machine job failed after all retry attempts")
            logger.info("=" * 60)
            return

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(f"Machine job completed in {elapsed:.2f}s")
        logger.info("=" * 60)

    except ScraperException as e:
        logger.error(f"Machine job failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in machine job: {e}", exc_info=True)
    finally:
        # Always cleanup: quit driver first
        session_manager = session_manager_holder.get("session_manager")
        if session_manager:
            try:
                session_manager.quit_driver()
            except Exception as cleanup_error:
                logger.error(f"Error during driver cleanup: {cleanup_error}")
        
        # Release lock if still held
        if lock.held:
            lock.release()


def run_once() -> None:
    """Run machine scraping once and exit."""
    logger.info("Running machine scraper in one-time mode...")
    try:
        machine_job()
        logger.info("One-time machine scraping completed")
    except Exception as e:
        logger.error(f"One-time machine scraping failed: {e}")
        sys.exit(1)


def run_scheduled() -> None:
    """
    Start scheduler: run machine_job every 6 hours.
    Keeps the process alive. Use this for long-running server deployments.
    """
    try:
        Config.validate()
        logger.info("Configuration validation passed")

        scheduler = BackgroundScheduler()

        # Run every 6 hours: at 00:00, 06:00, 12:00, 18:00 UTC
        scheduler.add_job(
            machine_job,
            "cron",
            hour="0,6,12,18",
            minute=0,
            timezone="UTC",
            id="machine_job",
        )

        scheduler.start()
        logger.info("Machine scheduler started — runs every 6 hours at 00:00, 06:00, 12:00, 18:00 UTC")
        logger.info("Press Ctrl+C to stop")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")

    except Exception as e:
        logger.error(f"Machine scheduler error: {e}")
        sys.exit(1)
    finally:
        if "scheduler" in locals() and scheduler.running:
            scheduler.shutdown()
            logger.info("Machine scheduler shut down")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Machine temperature scraper — runs independently every 6 hours",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run once (for testing or manual trigger)
  python machine.py --run-once

  # Start long-running scheduler (every 6 hours)
  python machine.py --schedule

Crontab (preferred for server):
  # Every 6 hours via cron (no date args needed)
  0 */6 * * * cd /app && venv/bin/python machine.py --run-once >> logs/machine_cron.log 2>&1
        """,
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Scrape machines once and exit",
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run APScheduler every 6 hours (long-running process)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )

    args = parser.parse_args()

    if args.run_once:
        run_once()
    elif args.schedule:
        run_scheduled()
    else:
        # Default: run once
        logger.info("No mode specified, running once...")
        run_once()


if __name__ == "__main__":
    main()
