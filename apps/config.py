"""
Configuration module for Build-Report application.
Loads settings from environment variables.
"""
import os
from typing import Set
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', '/opt/stroykontrol/database/stroykontrol.db')

    # API Server
    API_HOST: str = os.getenv('API_HOST', '127.0.0.1')
    API_PORT: int = int(os.getenv('API_PORT', '8000'))

    # CORS
    CORS_ORIGINS: list = os.getenv('CORS_ORIGINS', 'https://build-report.ru').split(',')

    # Telegram Bot
    BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
    MANAGER_USER_IDS: Set[int] = set()

    # Yandex Disk
    YANDEX_DISK_TOKEN: str = os.getenv('YANDEX_DISK_TOKEN', '')
    YANDEX_DISK_BASE_FOLDER: str = os.getenv('YANDEX_DISK_BASE_FOLDER', 'StroyKontrol')
    YANDEX_DISK_PEOPLE_REPORTS_FOLDER: str = os.getenv('YANDEX_DISK_PEOPLE_REPORTS_FOLDER', 'Фото отчеты (Люди)')

    # Security
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'change-me-in-production')

    # VAT
    VAT_RATE: float = float(os.getenv('VAT_RATE', '0.2'))

    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', '/var/log/stroykontrol.log')

    # Timezone
    TIMEZONE: str = os.getenv('TIMEZONE', 'Europe/Moscow')

    @classmethod
    def load_manager_ids(cls) -> Set[int]:
        """Load manager IDs from environment variable."""
        ids_str = os.getenv('MANAGER_USER_IDS', '')
        if not ids_str:
            return set()
        try:
            return {int(id_.strip()) for id_ in ids_str.split(',') if id_.strip()}
        except ValueError:
            return set()

    @property
    def vat_multiplier(self) -> float:
        """Calculate VAT multiplier."""
        return 1 + self.VAT_RATE


# Global settings instance
settings = Settings()
settings.MANAGER_USER_IDS = settings.load_manager_ids()
