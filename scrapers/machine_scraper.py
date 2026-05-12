"""
Machine list scraper.
Navigates machinelist.html, clicks each machine, extracts temperature from detail page.
"""
import time
import re
from typing import List, Optional
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from models.machine_data import MachineRecord, MachineScrapingResult
from utils.logging_setup import logger

# Base URL for machine list pagination
MACHINE_LIST_BASE = "/hbshengma/mobile/machinelist.html"

# Chinese labels for temperature field on detail page (multiple fallbacks)
_TEMPERATURE_LABELS = ["温度", "设备温度", "机器温度", "temp", "temperature"]


class MachineTemperatureScraper:
    """
    Scrape temperature from each machine's detail page.

    Strategy:
    1. Navigate to machinelist.html?pageno=1
    2. Collect all machine links on the page
    3. For each machine link: open detail page, extract temperature, come back
    4. Increment pageno until no more machines found
    """

    def __init__(self, driver, base_url: str):
        self._driver = driver
        self._base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scrape_all(self) -> MachineScrapingResult:
        """
        Scrape all machines across all list pages.
        Returns MachineScrapingResult with all records.
        """
        result = MachineScrapingResult()
        pageno = 1

        while True:
            list_url = f"{self._base_url}{MACHINE_LIST_BASE}?pageno={pageno}"
            logger.info(f"Machine list page {pageno}: {list_url}")

            self._driver.get(list_url)
            try:
                WebDriverWait(self._driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                logger.warning(f"Machine list page {pageno} did not load in time")
                break

            time.sleep(1.5)

            # Collect machine entries from list page
            machine_entries = self._collect_machine_entries()
            if not machine_entries:
                logger.info(f"No machines found on page {pageno}, stopping pagination")
                break

            logger.info(f"Found {len(machine_entries)} machines on page {pageno}")

            for idx, (detail_url, list_info) in enumerate(machine_entries, 1):
                try:
                    record = self._scrape_machine_detail(detail_url, list_info)
                    result.records.append(record)
                    logger.info(
                        f"  Machine {idx}/{len(machine_entries)}: "
                        f"{record.machine_code or '?'} | {record.machine_name or '?'} | "
                        f"temp={record.temperature or 'N/A'}"
                    )
                except Exception as exc:
                    msg = f"Failed to scrape machine detail {detail_url}: {exc}"
                    logger.error(msg)
                    result.errors.append(msg)
                    # Navigate back to list before continuing
                    self._driver.get(list_url)
                    time.sleep(1)

            # Check if there is a next page
            if not self._has_next_page():
                logger.info(f"No next page after machine list page {pageno}")
                break

            pageno += 1

        result.finalize()
        logger.info(
            f"Machine scraping complete: {result.record_count} records, "
            f"{len(result.errors)} errors"
        )
        return result

    # ------------------------------------------------------------------
    # Machine list parsing
    # ------------------------------------------------------------------

    def _collect_machine_entries(self) -> List[tuple]:
        """
        Parse current machine list page.
        Returns list of (detail_url, {code, name, ...}) tuples.
        """
        html = self._driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        entries = []

        # Strategy 1: <li> or <div> cards with an <a> tag linking to detail
        # Common patterns: machinedetail.html, devicedetail.html, detail?id=...
        detail_links = soup.find_all(
            "a",
            href=lambda h: h and (
                "machinedetail" in h.lower()
                or "devicedetail" in h.lower()
                or "machineinfo" in h.lower()
                or ("machine" in h.lower() and "list" not in h.lower())
            ),
        )

        if detail_links:
            for a_tag in detail_links:
                href = a_tag.get("href", "")
                full_url = self._resolve_url(href)
                # Try to extract code/name from the list item text
                parent = a_tag.find_parent(["li", "div", "tr"]) or a_tag
                list_info = self._extract_list_item_info(parent)
                entries.append((full_url, list_info))
            return entries

        # Strategy 2: table rows with clickable links
        for row in soup.find_all("tr")[1:]:
            a_tag = row.find("a", href=True)
            if a_tag:
                href = a_tag.get("href", "")
                full_url = self._resolve_url(href)
                list_info = self._extract_list_item_info(row)
                entries.append((full_url, list_info))

        return entries

    def _extract_list_item_info(self, element) -> dict:
        """Extract machine code and name from a list item element."""
        text = element.get_text(separator=" ", strip=True)
        info = {"raw_text": text}

        # Try to parse machine code: often alphanumeric, e.g. "9fl9g4hgn0f243c"
        # or labeled as 设备ID, 编号, etc.
        code_patterns = [
            r"设备ID[：:]\s*(\S+)",
            r"编号[：:]\s*(\S+)",
            r"ID[：:]\s*(\S+)",
            r"机器码[：:]\s*(\S+)",
        ]
        for pat in code_patterns:
            m = re.search(pat, text)
            if m:
                info["machine_code"] = m.group(1)
                break

        # Machine name: usually Chinese + alphanumeric after "名称" or at start
        name_patterns = [
            r"名称[：:]\s*(.+?)(?:\s{2,}|$)",
            r"设备名称[：:]\s*(.+?)(?:\s{2,}|$)",
        ]
        for pat in name_patterns:
            m = re.search(pat, text)
            if m:
                info["machine_name"] = m.group(1).strip()
                break

        return info

    def _has_next_page(self) -> bool:
        """Check if there is a next page button on the machine list."""
        try:
            nxt = self._driver.find_element(By.CSS_SELECTOR, "li.am-pagination-next")
            classes = nxt.get_attribute("class") or ""
            return "am-disabled" not in classes
        except NoSuchElementException:
            pass

        try:
            btn = self._driver.find_element(
                By.XPATH, "//*[contains(text(),'下一页') and not(@disabled)]"
            )
            classes = btn.get_attribute("class") or ""
            return "disabled" not in classes.lower()
        except NoSuchElementException:
            pass

        return False

    # ------------------------------------------------------------------
    # Machine detail page
    # ------------------------------------------------------------------

    def _scrape_machine_detail(self, url: str, list_info: dict) -> MachineRecord:
        """
        Navigate to machine detail page, extract temperature and other fields.
        """
        self._driver.get(url)
        try:
            WebDriverWait(self._driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            logger.warning(f"Detail page did not load in time: {url}")

        time.sleep(1.5)

        html = self._driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        record = MachineRecord(scrape_timestamp=datetime.now(timezone.utc))

        # Populate from list info if available
        record.machine_code = list_info.get("machine_code")
        record.machine_name = list_info.get("machine_name")

        # Extract all key-value pairs from detail page
        # Pattern 1: label-value pairs in spans/divs/tds
        detail_data = self._extract_key_value_pairs(soup)
        logger.debug(f"Detail page keys found: {list(detail_data.keys())}")

        # Map known Chinese keys to model fields
        _FIELD_MAP = {
            # temperature
            "温度": "temperature",
            "设备温度": "temperature",
            "机器温度": "temperature",
            "当前温度": "temperature",
            # machine code
            "设备ID": "machine_code",
            "编号": "machine_code",
            "机器码": "machine_code",
            "设备编号": "machine_code",
            # machine name
            "设备名称": "machine_name",
            "机器名称": "machine_name",
            "名称": "machine_name",
            # status
            "状态": "machine_status",
            "设备状态": "machine_status",
            "运行状态": "machine_status",
            # location
            "位置": "location",
            "地址": "location",
            "安装位置": "location",
            "设备位置": "location",
        }

        for cn_key, field_name in _FIELD_MAP.items():
            value = detail_data.get(cn_key)
            if value and not getattr(record, field_name):
                setattr(record, field_name, value)

        # Parse temperature unit if embedded in value (e.g. "25°C", "25℃")
        if record.temperature:
            t = record.temperature.strip()
            unit_match = re.search(r"(°C|℃|°F|℉|°)", t)
            if unit_match:
                record.temperature_unit = unit_match.group(1)
                record.temperature = t[: unit_match.start()].strip()
            else:
                record.temperature_unit = "°C"  # assume Celsius

        # Fallback: if code/name still missing, try to get from page title or heading
        if not record.machine_code or not record.machine_name:
            self._fill_from_heading(soup, record)

        return record

    def _extract_key_value_pairs(self, soup: BeautifulSoup) -> dict:
        """
        Extract key-value pairs from the detail page.
        Handles multiple common layouts:
        - <span class="label">Key</span><span class="value">Val</span>
        - <li>Key: Value</li>
        - <tr><td>Key</td><td>Val</td></tr>
        - <div class="am-u-sm-4">Key</div><div class="am-u-sm-8">Value</div>
        """
        data = {}

        # Pattern 1: <tr> rows with 2 <td> cells
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) == 2:
                key = cells[0].get_text(strip=True).rstrip("：:")
                val = cells[1].get_text(strip=True)
                if key and val:
                    data[key] = val
            elif len(cells) >= 4:
                # Multi-column table: treat as key-value pairs
                for i in range(0, len(cells) - 1, 2):
                    key = cells[i].get_text(strip=True).rstrip("：:")
                    val = cells[i + 1].get_text(strip=True)
                    if key and val:
                        data[key] = val

        # Pattern 2: AmyUI grid layout (am-u-sm-* divs)
        # <div class="am-u-sm-4 ...">Label</div>
        # <div class="am-u-sm-8 ...">Value</div>
        grid_divs = soup.find_all("div", class_=re.compile(r"am-u-sm-\d+"))
        for i in range(len(grid_divs) - 1):
            key = grid_divs[i].get_text(strip=True).rstrip("：:")
            val = grid_divs[i + 1].get_text(strip=True)
            if key and val and len(key) < 20:  # labels are short
                data[key] = val

        # Pattern 3: <li> items with "Key: Value" or "Key：Value"
        for li in soup.find_all("li"):
            text = li.get_text(strip=True)
            for sep in ["：", ":"]:
                if sep in text:
                    parts = text.split(sep, 1)
                    key = parts[0].strip()
                    val = parts[1].strip()
                    if key and val and len(key) < 20:
                        data[key] = val
                    break

        # Pattern 4: span pairs (label + value)
        spans = soup.find_all("span")
        for i in range(len(spans) - 1):
            key = spans[i].get_text(strip=True).rstrip("：:")
            if any(label in key for label in _TEMPERATURE_LABELS) or key in (
                "设备ID", "设备名称", "状态", "位置", "编号"
            ):
                val = spans[i + 1].get_text(strip=True)
                if val:
                    data[key] = val

        return data

    def _fill_from_heading(self, soup: BeautifulSoup, record: MachineRecord) -> None:
        """Try to get machine code/name from page heading or title."""
        for tag in ["h1", "h2", "h3", "h4", "title"]:
            el = soup.find(tag)
            if el:
                text = el.get_text(strip=True)
                if text and not record.machine_name:
                    record.machine_name = text
                break

    def _resolve_url(self, href: str) -> str:
        """Convert relative href to absolute URL."""
        if href.startswith("http"):
            return href
        if href.startswith("/"):
            return f"{self._base_url}{href}"
        # Relative path — assume same directory as machinelist
        return f"{self._base_url}/hbshengma/mobile/{href}"
