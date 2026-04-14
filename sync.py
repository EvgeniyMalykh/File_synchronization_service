"""Модуль синхронизации локальной папки с облачным хранилищем."""

import hashlib
import logging
import os

from cloud_storage import (
    CloudStorageError,
    DeleteError,
    InfoRetrievalError,
    UploadError,
)

logger = logging.getLogger(__name__)

BUFFER_SIZE = 65536


def get_file_md5(file_path):
    """Вычисление MD5-хеша файла.

    Args:
        file_path: Путь к файлу.

    Returns:
        MD5-хеш файла в виде строки.
    """
    md5 = hashlib.md5()
    with open(file_path, "rb") as file:
        buffer = file.read(BUFFER_SIZE)
        while buffer:
            md5.update(buffer)
            buffer = file.read(BUFFER_SIZE)
    return md5.hexdigest()


def get_local_files(local_folder):
    """Получение словаря локальных файлов с их MD5-хешами.

    Args:
        local_folder: Путь к локальной папке.

    Returns:
        Словарь {имя_файла: md5_хеш}.

    Raises:
        OSError: При ошибке чтения папки или файла.
    """
    local_files = {}
    for filename in os.listdir(local_folder):
        file_path = os.path.join(local_folder, filename)
        if not os.path.isfile(file_path):
            continue
        file_hash = get_file_md5(file_path)
        local_files[filename] = file_hash
    return local_files


def find_new_files(local_files, cloud_files):
    """Определение новых файлов, отсутствующих в облаке.

    Args:
        local_files: Словарь локальных файлов {имя: md5}.
        cloud_files: Словарь облачных файлов {имя: md5}.

    Returns:
        Список имён новых файлов.
    """
    return [name for name in local_files if name not in cloud_files]


def find_modified_files(local_files, cloud_files):
    """Определение изменённых файлов (хеш не совпадает).

    Args:
        local_files: Словарь локальных файлов {имя: md5}.
        cloud_files: Словарь облачных файлов {имя: md5}.

    Returns:
        Список имён изменённых файлов.
    """
    modified = []
    for name, local_hash in local_files.items():
        if name not in cloud_files:
            continue
        if local_hash != cloud_files[name]:
            modified.append(name)
    return modified


def find_deleted_files(local_files, cloud_files):
    """Определение удалённых файлов (есть в облаке, нет локально).

    Args:
        local_files: Словарь локальных файлов {имя: md5}.
        cloud_files: Словарь облачных файлов {имя: md5}.

    Returns:
        Список имён удалённых файлов.
    """
    return [name for name in cloud_files if name not in local_files]


def upload_new_files(storage, local_folder, new_files):
    """Загрузка новых файлов в облачное хранилище.

    Args:
        storage: Объект облачного хранилища.
        local_folder: Путь к локальной папке.
        new_files: Список имён новых файлов.
    """
    for filename in new_files:
        file_path = os.path.join(local_folder, filename)
        try:
            storage.load(file_path)
        except UploadError as error:
            logger.error(
                "Ошибка загрузки файла '%s': %s",
                filename,
                error,
            )


def reload_modified_files(storage, local_folder, modified_files):
    """Перезапись изменённых файлов в облачном хранилище.

    Args:
        storage: Объект облачного хранилища.
        local_folder: Путь к локальной папке.
        modified_files: Список имён изменённых файлов.
    """
    for filename in modified_files:
        file_path = os.path.join(local_folder, filename)
        try:
            storage.reload(file_path)
        except UploadError as error:
            logger.error(
                "Ошибка перезаписи файла '%s': %s",
                filename,
                error,
            )


def delete_removed_files(storage, deleted_files):
    """Удаление файлов из облачного хранилища.

    Args:
        storage: Объект облачного хранилища.
        deleted_files: Список имён удалённых файлов.
    """
    for filename in deleted_files:
        try:
            storage.delete(filename)
        except DeleteError as error:
            logger.error(
                "Ошибка удаления файла '%s': %s",
                filename,
                error,
            )


def synchronize(storage, local_folder):
    """Выполнение одного цикла синхронизации.

    Args:
        storage: Объект облачного хранилища.
        local_folder: Путь к локальной папке.
    """
    try:
        local_files = get_local_files(local_folder)
    except OSError as error:
        logger.error("Ошибка чтения локальной папки: %s", error)
        return

    try:
        cloud_files = storage.get_info()
    except InfoRetrievalError as error:
        logger.error(
            "Ошибка получения данных из хранилища: %s", error
        )
        return

    new_files = find_new_files(local_files, cloud_files)
    modified_files = find_modified_files(local_files, cloud_files)
    deleted_files = find_deleted_files(local_files, cloud_files)

    upload_new_files(storage, local_folder, new_files)
    reload_modified_files(storage, local_folder, modified_files)
    delete_removed_files(storage, deleted_files)

    logger.info(
        "Синхронизация завершена. "
        "Новых: %d, изменённых: %d, удалённых: %d.",
        len(new_files),
        len(modified_files),
        len(deleted_files),
    )
