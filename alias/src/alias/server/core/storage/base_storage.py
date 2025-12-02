# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from enum import Enum
from typing import List


class StorageType(str, Enum):
    LOCAL = "local"
    OSS = "oss"
    SANDBOX = "sandbox"


class BaseStorage(ABC):
    type: StorageType = None

    @abstractmethod
    def get_size(self, filename: str) -> int:  # mypy: ignore
        pass

    @property
    def storage_type(self) -> StorageType:
        return self.type

    @abstractmethod
    def save_file(self, filename: str, data: bytes) -> None:
        pass

    @abstractmethod
    def load_file(self, filename: str) -> bytes:
        pass

    @abstractmethod
    def download_file(self, filename: str, target_filename: str) -> None:
        pass

    @abstractmethod
    def copy_file(self, src: str, dst: str) -> None:
        pass

    @abstractmethod
    def exists(self, filename: str) -> bool:
        pass

    @abstractmethod
    def list_files(self, directory: str) -> List[str]:
        pass

    @abstractmethod
    def delete_file(self, filename: str) -> None:
        pass

    def create_directory(self, directory: str) -> str:
        return directory

    @abstractmethod
    def delete_directory(self, directory: str) -> None:
        pass
