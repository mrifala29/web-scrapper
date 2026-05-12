"""
Data models for machine temperature scraping.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MachineRecord(BaseModel):
    """Single machine record with temperature reading."""
    scrape_timestamp: datetime = Field(default_factory=_utcnow)
    machine_code: Optional[str] = None
    machine_name: Optional[str] = None
    temperature: Optional[str] = None
    temperature_unit: Optional[str] = None
    machine_status: Optional[str] = None
    location: Optional[str] = None


class MachineScrapingResult(BaseModel):
    """Result of one full machine list scrape run."""
    scrape_timestamp: datetime = Field(default_factory=_utcnow)
    records: List[MachineRecord] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    record_count: int = 0

    def finalize(self) -> "MachineScrapingResult":
        self.record_count = len(self.records)
        return self
