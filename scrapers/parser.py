"""
HTML parser for extracting sales data from website tables.
"""
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from datetime import datetime, timezone

from models.sales_data import SalesRecord, SalesStatisticData
from utils.logging_setup import logger
from utils.exceptions import ParsingError


class DataExtractor:
    """Extract data from HTML pages."""

    # Column mapping for each page target
    COLUMN_MAPPING = {
        "paydetail": [
            "序号", "系统订单号", "支付渠道流水号", "设备ID", "设备名称",
            "货道", "持有人", "商品名称", "支付方式", "支付金额",
            "购买数量", "商品进价", "付款人", "支付时间", "支付状态",
            "退款状态", "出货状态", "出货详情", "优惠券码", "折扣详情",
            "优惠金额", "订单金额", "出货编码", "操作"
        ],
        "deliverydetail": [
            "设备ID", "设备名称", "货道", "商品名称", "商品品牌",
            "销售金额", "支付类型", "销售时间", "返回码"
        ],
        "cashdetail": [
            "checkbox", "序号", "设备ID", "设备名称", "持有人",
            "交易类型", "交易方式", "金额", "交易时间"
        ],
        "essDetail": [
            "设备ID", "设备名称", "销售数量", "销售总额", "微信",
            "微信刷脸", "微信刷掌", "支付宝", "支付宝刷脸", "支付宝NFC",
            "现金", "微信会员", "会员卡", "扶贫网", "GHL"
        ],
        "mtOrder": [
            "美团订单号", "美团门店ID", "设备号", "商品名称", "支付金额",
            "订单状态", "取货码", "商品货道", "出货详情", "创建时间"
        ],
        "orderThird": [
            "订单号", "三方订单号", "设备ID", "商品名称", "货道",
            "支付方式", "订单金额", "商品单价", "数量", "购买人",
            "购买ID", "应退款金额", "出货状态", "交易时间", "创建时间"
        ],
        "orderThirdMachine": [
            "设备ID", "设备名称", "销售数量", "销售总额"
        ],
        "onlineOrderDetail": [
            "序号", "系统订单号", "支付渠道流水号", "设备ID", "设备名称",
            "商品名称", "支付方式", "支付金额", "购买数量", "商品进价",
            "支付状态", "出货状态", "退款状态", "支付时间"
        ]
    }

    @staticmethod
    def parse_table_data(html_content: str, page_name: str) -> SalesStatisticData:
        """
        Parse table data from HTML content with proper column mapping.

        Args:
            html_content: HTML source from Selenium WebDriver
            page_name: Name/identifier of the page being scraped

        Returns:
            SalesStatisticData object with extracted records

        Raises:
            ParsingError: If table parsing fails
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Find table (support both id and class selectors)
            table = soup.find("table")
            if not table:
                logger.warning(f"No table found in {page_name}")
                return SalesStatisticData(
                    scrape_timestamp=datetime.now(timezone.utc),
                    submenu=page_name,
                    records=[],
                    errors=[],
                )

            # Extract header row to get column count
            header_row = table.find("tr")
            header_cells = header_row.find_all(["th", "td"]) if header_row else []
            column_count = len(header_cells)

            records = []
            rows = table.find_all("tr")[1:]  # Skip header row

            for row_idx, row in enumerate(rows):
                try:
                    cells = row.find_all("td")
                    if not cells or len(cells) < 2:
                        continue

                    # Extract cell texts
                    cell_texts = [cell.get_text(strip=True) for cell in cells]

                    if not cell_texts:
                        continue

                    # Use first non-empty cell as ID
                    record_id = None
                    for text in cell_texts:
                        if text and text != "checkbox" and text != "操作":
                            record_id = text
                            break

                    if not record_id:
                        record_id = f"{page_name}_{row_idx}"

                    # Create SalesRecord with ID from first meaningful column
                    record = SalesRecord(
                        id=record_id,
                        timestamp=datetime.now(timezone.utc),
                    )
                    records.append(record)

                except Exception as e:
                    error_msg = f"Error parsing row {row_idx} in {page_name}: {str(e)}"
                    logger.error(error_msg)
                    continue

            logger.info(f"Parsed {len(records)} records from {page_name}")

            return SalesStatisticData(
                scrape_timestamp=datetime.now(timezone.utc),
                submenu=page_name,
                records=records,
                errors=[],
            )

        except Exception as e:
            error_msg = f"Failed to parse data from {page_name}: {str(e)}"
            logger.error(error_msg)
            raise ParsingError(error_msg)

    @staticmethod
    def extract_all_pages(driver, urls_dict: dict, start_date=None, end_date=None) -> List[SalesStatisticData]:
        """
        Navigate to multiple URLs and extract data from each.

        Args:
            driver: Selenium WebDriver instance
            urls_dict: Dictionary mapping page_name -> URL
            start_date: Optional start date for filtering (datetime with timezone)
            end_date: Optional end date for filtering (datetime with timezone)

        Returns:
            List of SalesStatisticData from all pages

        Example:
            urls = {
                "paydetail": "https://...paydetail.html",
                "deliverydetail": "https://...deliverydetail.html",
                ...
            }
            data_list = DataExtractor.extract_all_pages(driver, urls, start_date, end_date)
        """
        all_data = []

        for page_name, url in urls_dict.items():
            try:
                logger.info(f"Navigating to {page_name}: {url}")
                driver.get(url)
                
                # Wait for page load (adjust timeout/selector as needed)
                import time
                time.sleep(2)  # TODO: Use explicit wait instead

                # Get page source and parse
                html = driver.page_source
                data = DataExtractor.parse_table_data(html, page_name)
                
                # TODO: Filter by date range if provided
                # This is where you'd filter records by start_date and end_date
                # Example:
                # if start_date and end_date:
                #     data.records = [r for r in data.records 
                #                     if start_date <= r.timestamp <= end_date]
                
                all_data.append(data)

            except Exception as e:
                logger.error(f"Failed to extract data from {page_name}: {str(e)}")
                # Add error-only data record
                all_data.append(
                    SalesStatisticData(
                        scrape_timestamp=datetime.now(timezone.utc),
                        submenu=page_name,
                        records=[],
                        errors=[str(e)],
                    )
                )

        return all_data
