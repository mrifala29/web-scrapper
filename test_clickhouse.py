#!/usr/bin/env python3
"""
Test ClickHouse connection dan insert dummy data ke deliverydetail.
Jalankan: python test_clickhouse.py
"""
import sys
from datetime import datetime, date, timezone
from dotenv import load_dotenv
from pathlib import Path

# Load environment
load_dotenv()

import clickhouse_connect
from config.config import Config

# Dummy data untuk deliverydetail
DUMMY_DATA = [
    {
        "scrape_date": date(2026, 5, 6),
        "scrape_timestamp": datetime(2026, 5, 6, 12, 30, 0, tzinfo=timezone.utc),
        "device_id": "TEST001",
        "device_name": "Test Device 1",
        "aisle": "货道1",
        "product_name": "Test Product A",
        "product_brand": "Brand A",
        "sales_amount": "100.50",
        "payment_type": "现金",
        "sales_time": "2026-05-06 12:30:00",
        "return_code": "0000",
    },
    {
        "scrape_date": date(2026, 5, 6),
        "scrape_timestamp": datetime(2026, 5, 6, 12, 45, 0, tzinfo=timezone.utc),
        "device_id": "TEST002",
        "device_name": "Test Device 2",
        "aisle": "货道2",
        "product_name": "Test Product B",
        "product_brand": "Brand B",
        "sales_amount": "250.75",
        "payment_type": "微信",
        "sales_time": "2026-05-06 12:45:00",
        "return_code": "0000",
    },
    {
        "scrape_date": date(2026, 5, 6),
        "scrape_timestamp": datetime(2026, 5, 6, 13, 0, 0, tzinfo=timezone.utc),
        "device_id": "TEST003",
        "device_name": "Test Device 3",
        "aisle": "货道3",
        "product_name": "Test Product C",
        "product_brand": "Brand C",
        "sales_amount": "50.25",
        "payment_type": "支付宝",
        "sales_time": "2026-05-06 13:00:00",
        "return_code": "0000",
    },
]


def test_http_connection() -> bool:
    """Test using HTTP API (port 8123)."""
    print("\n[TEST 1] HTTP Connection (port 8123)")
    print("=" * 60)
    try:
        client = clickhouse_connect.get_client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_PORT,
            database=Config.CLICKHOUSE_DATABASE,
            username=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD,
            secure=False,
            connect_timeout=10,
        )
        print(f"✓ Connected via HTTP: {Config.CLICKHOUSE_HOST}:{Config.CLICKHOUSE_PORT}")

        # Test query
        result = client.query("SELECT version()")
        version = result.result_rows[0][0]
        print(f"✓ ClickHouse version: {version}")

        # List tables
        result = client.query("SHOW TABLES FROM hbshengma")
        tables = [row[0] for row in result.result_rows]
        print(f"✓ Database hbshengma has {len(tables)} tables: {', '.join(sorted(tables))}")

        client.close()
        return True
    except Exception as e:
        print(f"✗ HTTP connection failed: {e}")
        return False


def test_native_connection() -> bool:
    """Test using Native TCP (port 9000)."""
    print("\n[TEST 2] Native TCP Connection (port 9000)")
    print("=" * 60)
    try:
        client = clickhouse_connect.get_client(
            host=Config.CLICKHOUSE_HOST,
            port=9000,
            database=Config.CLICKHOUSE_DATABASE,
            username=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD,
            secure=False,
            connect_timeout=10,
        )
        print(f"✓ Connected via Native TCP: {Config.CLICKHOUSE_HOST}:9000")

        result = client.query("SELECT version()")
        version = result.result_rows[0][0]
        print(f"✓ ClickHouse version: {version}")

        client.close()
        return True
    except Exception as e:
        print(f"✗ Native TCP connection failed: {e}")
        return False


def insert_dummy_data(client) -> None:
    """Insert dummy data into deliverydetail."""
    print("\n[TEST 3] Insert Dummy Data")
    print("=" * 60)

    # Convert to rows format
    rows = []
    columns = [
        "scrape_date",
        "scrape_timestamp",
        "device_id",
        "device_name",
        "aisle",
        "product_name",
        "product_brand",
        "sales_amount",
        "payment_type",
        "sales_time",
        "return_code",
    ]

    for record in DUMMY_DATA:
        row = [record[col] for col in columns]
        rows.append(row)

    try:
        # Delete existing test data for today first (prevent duplicates)
        client.command(
            "ALTER TABLE hbshengma.deliverydetail "
            "DELETE WHERE scrape_date = '2026-05-06' AND device_id LIKE 'TEST%'"
        )
        print("✓ Deleted existing test data")

        # Insert new data
        client.insert("hbshengma.deliverydetail", rows, column_names=columns)
        print(f"✓ Inserted {len(rows)} dummy records into deliverydetail")

        # Verify
        result = client.query(
            "SELECT COUNT(*) FROM hbshengma.deliverydetail "
            "WHERE device_id LIKE 'TEST%' AND scrape_date = '2026-05-06'"
        )
        count = result.result_rows[0][0]
        print(f"✓ Verified: {count} test records in table")

        # Show sample
        result = client.query(
            "SELECT device_id, device_name, sales_amount, payment_type "
            "FROM hbshengma.deliverydetail "
            "WHERE device_id LIKE 'TEST%' "
            "ORDER BY scrape_timestamp DESC LIMIT 3"
        )
        print("\nSample records inserted:")
        for row in result.result_rows:
            print(f"  - {row[0]} | {row[1]} | ${row[2]} | {row[3]}")

    except Exception as e:
        print(f"✗ Insert failed: {e}")
        raise


def main() -> None:
    print("╔" + "=" * 58 + "╗")
    print("║" + " ClickHouse Connection Test ".center(58) + "║")
    print("╚" + "=" * 58 + "╝")

    print(f"\nConfiguration:")
    print(f"  Host: {Config.CLICKHOUSE_HOST}")
    print(f"  Database: {Config.CLICKHOUSE_DATABASE}")
    print(f"  User: {Config.CLICKHOUSE_USER}")

    # Try HTTP first (more common for external access)
    http_ok = test_http_connection()

    # Try Native TCP as fallback
    native_ok = False
    if not http_ok:
        native_ok = test_native_connection()

    # If either works, try inserting data
    if http_ok or native_ok:
        port = Config.CLICKHOUSE_PORT if http_ok else 9000
        print(f"\n[INFO] Using HTTP API (port {port})")

        try:
            client = clickhouse_connect.get_client(
                host=Config.CLICKHOUSE_HOST,
                port=port,
                database=Config.CLICKHOUSE_DATABASE,
                username=Config.CLICKHOUSE_USER,
                password=Config.CLICKHOUSE_PASSWORD,
                secure=False,
                connect_timeout=10,
            )
            insert_dummy_data(client)
            client.close()

            print("\n" + "=" * 60)
            print("✓ ALL TESTS PASSED!")
            print("=" * 60)
            print("\nNext step: Run main scraper")
            print("  python main.py --run-once --yesterday")
        except Exception as e:
            print(f"\n✗ TEST FAILED: {e}")
            sys.exit(1)
    else:
        print("\n" + "=" * 60)
        print("✗ NO CONNECTION POSSIBLE")
        print("=" * 60)
        print("\nTroubleshooting:")
        print("  1. Check firewall/network access to ClickHouse")
        print("  2. Verify credentials in .env")
        print("  3. Ensure ClickHouse is running: docker ps")
        sys.exit(1)


if __name__ == "__main__":
    main()
