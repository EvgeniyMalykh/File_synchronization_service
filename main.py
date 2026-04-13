"""Главный модуль сервиса синхронизации файлов."""

import configparser
import logging
import os
import sys
import time

from cloud_storage import YandexDiskStorage
from sync import synchronize

CONFIG_FILE = "config.ini"


def read_config(config_path):
    """Чтение параметров из файла конфигурации.

    Args:
        config_path: Путь к файлу config.ini.

    Returns:
        Словарь с параметрами конфигурации.
    """
    config = configparser.ConfigParser()
    config.read(config_path)
    return {
        "local_folder": config.get("sync", "local_folder"),
        "cloud_folder": config.get("sync", "cloud_folder"),
        "token": config.get("sync", "token"),
        "sync_period": config.getint("sync", "sync_period"),
        "log_file": config.get("sync", "log_file"),
    }


def setup_logging(log_file):
    """Настройка логирования в файл и консоль.

    Args:
        log_file: Путь к файлу лога.
    """
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def validate_local_folder(local_folder):
    """Проверка существования локальной папки.

    Args:
        local_folder: Путь к локальной папке.
    """
    if not os.path.isdir(local_folder):
        print(
            f"Ошибка: папка '{local_folder}' не найдена. "
            "Проверьте параметр 'local_folder' в config.ini."
        )
        sys.exit(1)


def validate_token(token):
    """Проверка валидности токена доступа.

    Args:
        token: OAuth-токен Яндекс.Диска.
    """
    if not token or token == "YOUR_TOKEN_HERE":
        print(
            "Ошибка: укажите корректный OAuth-токен "
            "в параметре 'token' файла config.ini."
        )
        sys.exit(1)


def run_sync_loop(storage, local_folder, sync_period):
    """Запуск бесконечного цикла синхронизации.

    Args:
        storage: Объект облачного хранилища.
        local_folder: Путь к локальной папке.
        sync_period: Период синхронизации в секундах.
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "Запуск синхронизации. Папка: '%s'. Период: %d сек.",
        local_folder,
        sync_period,
    )
    while True:
        synchronize(storage, local_folder)
        time.sleep(sync_period)


def main():
    """Точка входа в программу."""
    try:
        settings = read_config(CONFIG_FILE)
    except (configparser.Error, KeyError) as error:
        print(
            f"Ошибка чтения config.ini: {error}. "
            "Проверьте формат и наличие всех параметров."
        )
        sys.exit(1)

    validate_local_folder(settings["local_folder"])
    validate_token(settings["token"])
    setup_logging(settings["log_file"])

    logger = logging.getLogger(__name__)
    logger.info("Программа запущена.")
    logger.info(
        "Синхронизируемая папка: '%s'.", settings["local_folder"]
    )

    storage = YandexDiskStorage(
        settings["token"], settings["cloud_folder"]
    )

    try:
        storage.ensure_folder_exists()
    except Exception as error:
        print(
            f"Ошибка доступа к облачному хранилищу: {error}. "
            "Проверьте параметр 'token' в config.ini."
        )
        sys.exit(1)

    run_sync_loop(
        storage, settings["local_folder"], settings["sync_period"]
    )


if __name__ == "__main__":
    main()
