"""Модуль для работы с облачным хранилищем Яндекс.Диск."""

import logging
import os

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://cloud-api.yandex.net/v1/disk/resources"


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
        """
        url = f"{BASE_URL}/upload"
        params = {"path": cloud_path, "overwrite": str(overwrite).lower()}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json().get("href")

    def load(self, path):
        """Загрузка нового файла в хранилище.

        Args:
            path: Локальный путь к загружаемому файлу.
        """
        filename = os.path.basename(path)
        cloud_path = f"{self.cloud_folder}/{filename}"
        upload_url = self._get_upload_url(cloud_path, overwrite=False)
        with open(path, "rb") as file:
            response = requests.put(upload_url, files={"file": file})
        response.raise_for_status()
        logger.info("Файл '%s' загружен в хранилище.", filename)

    def reload(self, path):
        """Перезапись файла в хранилище.

        Args:
            path: Локальный путь к файлу для перезаписи.
        """
        filename = os.path.basename(path)
        cloud_path = f"{self.cloud_folder}/{filename}"
        upload_url = self._get_upload_url(cloud_path, overwrite=True)
        with open(path, "rb") as file:
            response = requests.put(upload_url, files={"file": file})
        response.raise_for_status()
        logger.info("Файл '%s' перезаписан в хранилище.", filename)

    def delete(self, filename):
        """Удаление файла из хранилища.

        Args:
            filename: Имя файла для удаления.
        """
        cloud_path = f"{self.cloud_folder}/{filename}"
        params = {"path": cloud_path, "permanently": "false"}
        response = requests.delete(
            BASE_URL, headers=self.headers, params=params
        )
        response.raise_for_status()
        logger.info("Файл '%s' удалён из хранилища.", filename)

    def ensure_folder_exists(self):
        """Создание папки в хранилище, если она не существует."""
        params = {"path": self.cloud_folder}
        response = requests.get(
            BASE_URL, headers=self.headers, params=params
        )
        if response.status_code == 404:
            response = requests.put(
                BASE_URL, headers=self.headers, params=params
            )
            response.raise_for_status()
            logger.info(
                "Создана папка '%s' в облачном хранилище.",
                self.cloud_folder,
            )
            return
        response.raise_for_status()

    def get_info(self):
        """Получение информации о файлах в облачной папке.

        Returns:
            Словарь {имя_файла: md5_хеш} для файлов в облачной папке.
        """
        params = {"path": self.cloud_folder, "limit": 10000}
        response = requests.get(
            BASE_URL, headers=self.headers, params=params
        )
        response.raise_for_status()
        items = response.json().get("_embedded", {}).get("items", [])
        cloud_files = {}
        for item in items:
            if item.get("type") != "file":
                continue
            cloud_files[item["name"]] = item.get("md5", "")
        return cloud_files