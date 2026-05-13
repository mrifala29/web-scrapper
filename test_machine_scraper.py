#!/usr/bin/env python
"""
Test script: Machine temperature scraper (no ClickHouse connection required).

NOTE: Machine data is real-time current state (no date filtering).
Date range parameters are for API consistency with sales scraper, and logged for reference.

Usage:
    # Run and scrape current machine state (date range for reference only)
    python test_machine_scraper.py
    python test_machine_scraper.py --start-date 2026-01-01 --end-date 2026-12-31
    python test_machine_scraper.py --yesterday

Output:
    - Console: Detailed logs + table of results
    - File: machine_scraping_test_<timestamp>.json (with scrape_date = today)
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Setup paths
sys.path.insert(0, str(Path(__file__).parent))

from config.config import Config
from utils.logging_setup import logger
from utils.session_manager import SessionManager
from scrapers.auth_handler import LoginHandler
from scrapers.machine_scraper import MachineTemperatureScraper


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Test machine temperature scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_machine_scraper.py
  python test_machine_scraper.py --start-date 2026-01-01 --end-date 2026-01-31
  python test_machine_scraper.py --yesterday
        """,
    )
    
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--yesterday",
        action="store_true",
        help="Run for yesterday only",
    )
    
    return parser.parse_args()


def _parse_date(date_str: str) -> datetime:
    """Parse YYYY-MM-DD format to UTC datetime at 00:00:00."""
    if not date_str:
        return None
    parts = date_str.split("-")
    if len(parts) != 3:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")
    try:
        return datetime(int(parts[0]), int(parts[1]), int(parts[2]), tzinfo=timezone.utc)
    except ValueError as e:
        raise ValueError(f"Invalid date: {date_str}") from e


def main():
    """Test machine scraper locally."""
    args = parse_args()
    
    # Determine date range
    start_date = None
    end_date = None
    
    if args.yesterday:
        # Yesterday in UTC
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif args.start_date and args.end_date:
        start_date = _parse_date(args.start_date)
        end_date = _parse_date(args.end_date).replace(hour=23, minute=59, second=59)
    else:
        # Use default from config
        start_date = Config.get_start_date()
        end_date = Config.get_end_date()
    
    logger.info("=" * 70)
    logger.info("MACHINE SCRAPER TEST (Local, No ClickHouse)")
    logger.info("=" * 70)
    if start_date and end_date:
        logger.info(f"Date range (for reference): {start_date.date()} to {end_date.date()}")
    logger.info("Machine data is real-time current state (not date-filtered)\n")
    
    session_manager = None
    
    try:
        # Step 1: Initialize WebDriver
        logger.info("\nStep 1: Initializing WebDriver...")
        session_manager = SessionManager()
        session_manager.initialize_driver()
        logger.info("✓ WebDriver initialized")
        
        # Step 2: Login
        logger.info("\nStep 2: Logging in to website...")
        login_handler = LoginHandler(session_manager)
        if not login_handler.login():
            logger.error("✗ Login failed!")
            sys.exit(1)
        logger.info("✓ Login successful")
        
        # Step 3: Run machine scraper
        logger.info("\nStep 3: Scraping machines...")
        logger.info(f"  Base URL: {Config.BASE_URL}")
        logger.info("  Starting pagination from pageno=1...")
        
        scraper = MachineTemperatureScraper(
            driver=session_manager.driver,
            base_url=Config.BASE_URL,
        )
        result = scraper.scrape_all(start_date=start_date, end_date=end_date)
        
        logger.info(f"✓ Machine scraping completed")
        
        # Step 4: Display results
        logger.info("\n" + "=" * 70)
        logger.info("RESULTS")
        logger.info("=" * 70)
        logger.info(f"Total machines scraped: {result.record_count}")
        logger.info(f"Total errors: {len(result.errors)}")
        
        if result.errors:
            logger.warning("\nErrors encountered:")
            for err in result.errors:
                logger.warning(f"  - {err}")
        
        if result.records:
            logger.info("\nMachine Details:")
            logger.info("-" * 70)
            
            # Pretty print as table
            for idx, rec in enumerate(result.records, 1):
                logger.info(f"\n  Machine {idx}:")
                logger.info(f"    Code:      {rec.machine_code or 'N/A'}")
                logger.info(f"    Name:      {rec.machine_name or 'N/A'}")
                logger.info(f"    Temp:      {rec.temperature or 'N/A'} {rec.temperature_unit or ''}")
                logger.info(f"    Status:    {rec.machine_status or 'N/A'}")
                logger.info(f"    Location:  {rec.location or 'N/A'}")
                logger.info(f"    Timestamp: {rec.scrape_timestamp.isoformat()}")
        else:
            logger.warning("\nNo machines found!")
        
        # Step 5: Save to JSON
        output_dir = Path(Config.DATA_FOLDER)
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        output_file = output_dir / f"machine_scraping_test_{timestamp}.json"
        
        # Serialize records to JSON
        # Note: scrape_timestamp = when record was scraped (current run time)
        records_dict = [
            {
                "machine_code": rec.machine_code,
                "machine_name": rec.machine_name,
                "temperature": rec.temperature,
                "temperature_unit": rec.temperature_unit,
                "machine_status": rec.machine_status,
                "location": rec.location,
                "scrape_timestamp": rec.scrape_timestamp.isoformat(),
            }
            for rec in result.records
        ]
        
        today = datetime.now(timezone.utc).date().isoformat()
        output_data = {
            "test_run_timestamp": datetime.now(timezone.utc).isoformat(),
            "scrape_date": today,
            "note": "Machine data is real-time current state (not filtered by date range)",
            "total_records": result.record_count,
            "total_errors": len(result.errors),
            "errors": result.errors,
            "records": records_dict,
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n✓ Results saved to: {output_file}")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if session_manager:
            logger.info("\nClosing WebDriver...")
            session_manager.quit_driver()
            logger.info("✓ WebDriver closed")


if __name__ == "__main__":
    main()
