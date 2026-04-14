"""Модуль для работы с облачным хранилищем Яндекс.Диск."""

import logging
import os

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://cloud-api.yandex.net/v1/disk/resources"
REQUEST_TIMEOUT = 30


class CloudStorageError(Exception):
    """Базовое исключение для ошибок облачного хранилища."""


class UploadError(CloudStorageError):
    """Ошибка загрузки файла в хранилище."""


class DeleteError(CloudStorageError):
    """Ошибка удаления файла из хранилища."""


class FolderCreationError(CloudStorageError):
    """Ошибка создания папки в хранилище."""


class InfoRetrievalError(CloudStorageError):
    """Ошибка получения информации из хранилища."""


class YandexDiskStorage:
    """Класс для взаимодействия с Яндекс.Диском через REST API."""

    def __init__(self, token, cloud_folder):
        """Инициализация хранилища.

        Args:
            token: OAuth-токен для доступа к Яндекс.Диску.
            cloud_folder: Путь к папке в облачном хранилище.
        """
        self.token = token
        self.cloud_folder = cloud_folder
        self.headers = {"Authorization": f"OAuth {self.token}"}

    def _get_upload_url(self, cloud_path, overwrite=False):
        """Получение URL для загрузки файла.

        Args:
            cloud_path: Путь к файлу в облачном хранилище.
            overwrite: Перезаписать файл, если существует.

        Returns:
            URL для загрузки файла.

        Raises:
            UploadError: При ошибке получения URL.
        """
        url = f"{BASE_URL}/upload"
        params = {
            "path": cloud_path,
            "overwrite": str(overwrite).lower(),
        }
        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise UploadError(
                f"Таймаут при получении URL загрузки: {cloud_path}"
            )
        except requests.exceptions.ConnectionError:
            raise UploadError(
                "Нет соединения с сервером Яндекс.Диска."
            )
        except requests.exceptions.HTTPError as error:
            raise UploadError(
                f"HTTP-ошибка при получении URL загрузки: {error}"
            )
        return response.json().get("href")

    def load(self, path):
        """Загрузка нового файла в хранилище.

        Args:
            path: Локальный путь к загружаемому файлу.

        Raises:
            UploadError: При ошибке загрузки файла.
        """
        filename = os.path.basename(path)
        cloud_path = f"{self.cloud_folder}/{filename}"
        upload_url = self._get_upload_url(
            cloud_path, overwrite=False
        )
        try:
            with open(path, "rb") as file:
                response = requests.put(
                    upload_url,
                    files={"file": file},
                    timeout=REQUEST_TIMEOUT,
                )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise UploadError(
                f"Таймаут при загрузке файла '{filename}'."
            )
        except requests.exceptions.ConnectionError:
            raise UploadError(
                f"Нет соединения при загрузке '{filename}'."
            )
        except requests.exceptions.HTTPError as error:
            raise UploadError(
                f"HTTP-ошибка при загрузке '{filename}': {error}"
            )
        logger.info("Файл '%s' загружен в хранилище.", filename)

    def reload(self, path):
        """Перезапись файла в хранилище.

        Args:
            path: Локальный путь к файлу для перезаписи.

        Raises:
            UploadError: При ошибке перезаписи файла.
        """
        filename = os.path.basename(path)
        cloud_path = f"{self.cloud_folder}/{filename}"
        upload_url = self._get_upload_url(
            cloud_path, overwrite=True
        )
        try:
            with open(path, "rb") as file:
                response = requests.put(
                    upload_url,
                    files={"file": file},
                    timeout=REQUEST_TIMEOUT,
                )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise UploadError(
                f"Таймаут при перезаписи файла '{filename}'."
            )
        except requests.exceptions.ConnectionError:
            raise UploadError(
                f"Нет соединения при перезаписи '{filename}'."
            )
        except requests.exceptions.HTTPError as error:
            raise UploadError(
                f"HTTP-ошибка при перезаписи '{filename}': {error}"
            )
        logger.info(
            "Файл '%s' перезаписан в хранилище.", filename
        )

    def delete(self, filename):
        """Удаление файла из хранилища.

        Args:
            filename: Имя файла для удаления.

        Raises:
            DeleteError: При ошибке удаления файла.
        """
        cloud_path = f"{self.cloud_folder}/{filename}"
        params = {"path": cloud_path, "permanently": "false"}
        try:
            response = requests.delete(
                BASE_URL,
                headers=self.headers,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise DeleteError(
                f"Таймаут при удалении файла '{filename}'."
            )
        except requests.exceptions.ConnectionError:
            raise DeleteError(
                f"Нет соединения при удалении '{filename}'."
            )
        except requests.exceptions.HTTPError as error:
            raise DeleteError(
                f"HTTP-ошибка при удалении '{filename}': {error}"
            )
        logger.info("Файл '%s' удалён из хранилища.", filename)

    def ensure_folder_exists(self):
        """Создание папки в хранилище, если не существует.

        Raises:
            FolderCreationError: При ошибке создания папки.
        """
        params = {"path": self.cloud_folder}
        try:
            response = requests.get(
                BASE_URL,
                headers=self.headers,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.exceptions.Timeout:
            raise FolderCreationError(
                "Таймаут при проверке папки в хранилище."
            )
        except requests.exceptions.ConnectionError:
            raise FolderCreationError(
                "Нет соединения с сервером Яндекс.Диска."
            )
        if response.status_code == 404:
            try:
                response = requests.put(
                    BASE_URL,
                    headers=self.headers,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
            except requests.exceptions.Timeout:
                raise FolderCreationError(
                    "Таймаут при создании папки в хранилище."
                )
            except requests.exceptions.ConnectionError:
                raise FolderCreationError(
                    "Нет соединения при создании папки."
                )
            except requests.exceptions.HTTPError as error:
                raise FolderCreationError(
                    f"HTTP-ошибка при создании папки: {error}"
                )
            logger.info(
                "Создана папка '%s' в облачном хранилище.",
                self.cloud_folder,
            )
            return
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            raise FolderCreationError(
                f"HTTP-ошибка при проверке папки: {error}"
            )

    def get_info(self):
        """Получение информации о файлах в облачной папке.

        Returns:
            Словарь {имя_файла: md5_хеш} для файлов.

        Raises:
            InfoRetrievalError: При ошибке получения данных.
        """
        params = {"path": self.cloud_folder, "limit": 10000}
        try:
            response = requests.get(
                BASE_URL,
                headers=self.headers,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise InfoRetrievalError(
                "Таймаут при получении списка файлов."
            )
        except requests.exceptions.ConnectionError:
            raise InfoRetrievalError(
                "Нет соединения с сервером Яндекс.Диска."
            )
        except requests.exceptions.HTTPError as error:
            raise InfoRetrievalError(
                f"HTTP-ошибка при получении списка: {error}"
            )
        items = (
            response.json().get("_embedded", {}).get("items", [])
        )
        cloud_files = {}
        for item in items:
            if item.get("type") != "file":
                continue
            cloud_files[item["name"]] = item.get("md5", "")
        return cloud_files
