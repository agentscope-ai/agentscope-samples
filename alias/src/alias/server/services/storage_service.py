# -*- coding: utf-8 -*-
import uuid
from pathlib import Path
from typing import List

from alias.server.core.storage import StorageFactory


class StorageService:
    def __init__(self):
        self.storage = StorageFactory.get_storage()

    @property
    def storage_type(self):
        return self.storage.storage_type

    async def get_size(self, filename: str) -> int:
        return self.storage.get_size(filename)

    async def save_file(self, filename: str, data: bytes) -> None:
        self.storage.save_file(filename, data)

    async def load_file(self, filename: str) -> bytes:
        return self.storage.load_file(filename)

    async def download_file(self, filename: str, target_filename: str) -> None:
        self.storage.download_file(filename, target_filename)

    async def copy_file(self, src: str, dst: str) -> None:
        self.storage.copy_file(src, dst)

    async def delete_file(self, filename: str) -> None:
        self.storage.delete_file(filename)

    async def list_files(self, directory: Path) -> List[Path]:
        return [
            Path(file)
            for file in self.storage.list_files(directory=str(directory))
        ]

    async def exists(self, filename: Path) -> bool:
        return self.storage.exists(filename)

    async def create_directory(self, directory: Path) -> Path:
        return Path(self.storage.create_directory(directory))

    async def delete_directory(self, directory: Path) -> None:
        self.storage.delete_directory(directory)

    async def create_upload_directory(
        self,
        user_id: uuid.UUID,
        absolute: bool = False,
    ) -> Path:
        relative_upload_path = self._generate_upload_directory(user_id=user_id)
        upload_path = await self.create_directory(relative_upload_path)
        return upload_path if absolute else relative_upload_path

    async def get_upload_directory(self, user_id: uuid.UUID) -> Path:
        return await self.create_upload_directory(user_id=user_id)

    def _generate_upload_directory(self, user_id: uuid.UUID) -> Path:
        return Path(f"uploads/{user_id}")
