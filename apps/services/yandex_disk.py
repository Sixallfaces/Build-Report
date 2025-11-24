"""Yandex Disk service for file storage."""
import logging
import re
import requests
from typing import Optional

from apps.config import settings

logger = logging.getLogger('yandex_disk')


class YandexDiskService:
    """Service for working with Yandex Disk API."""

    BASE_URL = 'https://cloud-api.yandex.net/v1/disk'

    def __init__(self):
        self.token = settings.YANDEX_DISK_TOKEN
        self.base_folder = settings.YANDEX_DISK_BASE_FOLDER

    def _get_headers(self) -> Optional[dict]:
        """Get authorization headers."""
        if not self.token:
            logger.error("Yandex Disk token not configured")
            return None
        return {
            'Authorization': f'OAuth {self.token}',
            'Content-Type': 'application/json'
        }

    def check_connection(self) -> bool:
        """Check if Yandex Disk connection is working."""
        headers = self._get_headers()
        if not headers:
            return False

        try:
            response = requests.get(f'{self.BASE_URL}/', headers=headers, timeout=10)
            if response.status_code == 200:
                logger.info("Yandex Disk connection successful")
                return True
            logger.error(f"Yandex Disk connection failed: {response.status_code}")
        except requests.RequestException as exc:
            logger.error(f"Yandex Disk connection error: {exc}")
        return False

    def create_folder(self, folder_path: str) -> bool:
        """Create a folder on Yandex Disk."""
        headers = self._get_headers()
        if not headers:
            return False

        if not folder_path.startswith('/'):
            folder_path = '/' + folder_path

        try:
            response = requests.put(
                f'{self.BASE_URL}/resources',
                headers=headers,
                params={'path': folder_path},
                timeout=10
            )
            if response.status_code in (200, 201):
                logger.info(f"Folder created: {folder_path}")
                return True
            if response.status_code == 409:
                logger.debug(f"Folder already exists: {folder_path}")
                return True
            logger.error(f"Failed to create folder: {response.status_code} - {response.text}")
        except requests.RequestException as exc:
            logger.error(f"Error creating folder: {exc}")
        return False

    def publish_folder(self, folder_path: str) -> Optional[str]:
        """Publish a folder and return public URL."""
        headers = self._get_headers()
        if not headers:
            return None

        if folder_path.startswith('/'):
            folder_path = folder_path[1:]

        try:
            # Publish the folder
            publish_response = requests.put(
                f'{self.BASE_URL}/resources/publish',
                headers=headers,
                params={'path': folder_path},
                timeout=10
            )
            if publish_response.status_code not in (200, 201):
                logger.error(f"Failed to publish folder: {publish_response.status_code}")
                return None

            # Get public URL
            info_response = requests.get(
                f'{self.BASE_URL}/resources',
                headers=headers,
                params={'path': folder_path, 'fields': 'public_url'},
                timeout=10
            )
            if info_response.status_code == 200:
                public_url = info_response.json().get('public_url')
                if public_url:
                    # Sanitize URL
                    public_url = self._sanitize_url(public_url)
                    logger.info(f"Public URL: {public_url}")
                    return public_url
            logger.error(f"Failed to get public URL: {info_response.status_code}")
        except requests.RequestException as exc:
            logger.error(f"Error publishing folder: {exc}")
        return None

    def upload_file(self, file_data: bytes, file_path: str) -> Optional[str]:
        """Upload a file to Yandex Disk and return public URL."""
        headers = self._get_headers()
        if not headers:
            return None

        try:
            # Get upload URL
            response = requests.get(
                f'{self.BASE_URL}/resources/upload',
                headers=headers,
                params={'path': file_path, 'overwrite': 'true'},
                timeout=10
            )
            if response.status_code != 200:
                logger.error(f"Failed to get upload URL: {response.status_code}")
                return None

            href = response.json().get('href')
            if not href:
                logger.error("No upload URL in response")
                return None

            # Upload file
            upload_response = requests.put(href, data=file_data, timeout=60)
            if upload_response.status_code != 201:
                logger.error(f"Failed to upload file: {upload_response.status_code}")
                return None

            # Publish file
            publish_response = requests.put(
                f'{self.BASE_URL}/resources/publish',
                headers=headers,
                params={'path': file_path},
                timeout=10
            )
            if publish_response.status_code != 200:
                logger.warning(f"Failed to publish file: {publish_response.status_code}")
                return file_path

            # Get public URL
            info_response = requests.get(
                f'{self.BASE_URL}/resources',
                headers=headers,
                params={'path': file_path, 'fields': 'public_url'},
                timeout=10
            )
            if info_response.status_code == 200:
                return self._sanitize_url(info_response.json().get('public_url'))

            return file_path
        except requests.RequestException as exc:
            logger.error(f"Error uploading file: {exc}")
        return None

    @staticmethod
    def _sanitize_url(url: Optional[str]) -> Optional[str]:
        """Remove duplicate URLs from a string."""
        if not url:
            return url
        cleaned = url.strip()
        match = re.match(r'https?://.+?(?=https?:/{1,2}|$)', cleaned)
        return match.group(0) if match else cleaned

    @staticmethod
    def sanitize_folder_component(component: str) -> str:
        """Sanitize a folder name component."""
        safe = re.sub(r'[^\w\-]', '_', component or '')
        return safe or 'unknown'

    def ensure_report_folder(self, foreman_name: str, foreman_id: int, report_date: str) -> Optional[str]:
        """Create and publish a folder structure for a report."""
        if not self.check_connection():
            return None

        safe_foreman = self.sanitize_folder_component(foreman_name)
        safe_date = self.sanitize_folder_component(report_date)
        safe_base = self.sanitize_folder_component(self.base_folder)

        # Create folder structure
        base_path = f"/{safe_base}"
        if not self.create_folder(base_path):
            return None

        date_path = f"{base_path}/{safe_date}"
        if not self.create_folder(date_path):
            return None

        foreman_path = f"{date_path}/{safe_foreman}_ID_{foreman_id}"
        if not self.create_folder(foreman_path):
            return None

        return self.publish_folder(foreman_path)


# Global service instance
yandex_disk_service = YandexDiskService()
