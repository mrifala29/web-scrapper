"""
JSON storage handler for scraped data.
Manages data persistence with timestamps and backup.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from config.config import Config
from utils.logging_setup import logger
from utils.exceptions import StorageError


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""
    
    def default(self, obj):
        """Convert datetime to ISO format string."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class JSONStorage:
    """Handle JSON file storage for scraped data."""

    def __init__(self, folder: str = None):
        """
        Initialize JSON storage.

        Args:
            folder: Output folder path (defaults to Config.DATA_FOLDER)
        """
        self.folder = folder or Config.DATA_FOLDER
        self._ensure_folder()

    def _ensure_folder(self) -> None:
        """Create data folder if it doesn't exist."""
        Path(self.folder).mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured data folder exists: {self.folder}")

    def save_data(
        self, data: Dict[str, Any], filename: str = None
    ) -> str:
        """
        Save data to JSON file with timestamp.

        Args:
            data: Data dictionary to save
            filename: Custom filename (optional)

        Returns:
            Path to saved file

        Raises:
            StorageError: If save operation fails
        """
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filename = f"sales_data_{timestamp}.json"

            filepath = os.path.join(self.folder, filename)

            # Add metadata
            output_data = {
                "metadata": {
                    "saved_at": datetime.now().isoformat(),
                    "filename": filename,
                },
                "data": data,
            }

            # Write JSON
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)

            logger.info(f"Data saved successfully: {filepath}")
            return filepath

        except Exception as e:
            error_msg = f"Failed to save JSON data: {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg)

    def load_data(self, filename: str) -> Dict[str, Any]:
        """
        Load data from JSON file.

        Args:
            filename: Filename to load

        Returns:
            Data dictionary

        Raises:
            StorageError: If load operation fails
        """
        try:
            filepath = os.path.join(self.folder, filename)

            if not os.path.exists(filepath):
                raise FileNotFoundError(f"File not found: {filepath}")

            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            logger.info(f"Data loaded successfully: {filepath}")
            return data

        except Exception as e:
            error_msg = f"Failed to load JSON data: {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg)

    def list_files(self, pattern: str = "*.json") -> list:
        """
        List all JSON files in data folder.

        Args:
            pattern: File pattern to match

        Returns:
            List of filenames
        """
        try:
            files = sorted(Path(self.folder).glob(pattern))
            filenames = [f.name for f in files]
            logger.debug(f"Found {len(filenames)} JSON files")
            return filenames
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            return []

    def cleanup_old_files(self, keep_count: int = None) -> None:
        """
        Delete old files, keeping only recent ones.

        Args:
            keep_count: Number of recent files to keep (defaults to Config.KEEP_BACKUPS)
        """
        try:
            if keep_count is None:
                keep_count = Config.KEEP_BACKUPS

            files = sorted(Path(self.folder).glob("sales_data_*.json"))

            if len(files) > keep_count:
                files_to_delete = files[:-keep_count]
                for file in files_to_delete:
                    file.unlink()
                    logger.info(f"Deleted old file: {file.name}")

        except Exception as e:
            logger.error(f"Error cleaning up old files: {str(e)}")
