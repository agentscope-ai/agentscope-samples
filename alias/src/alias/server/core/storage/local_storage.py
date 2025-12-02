# -*- coding: utf-8 -*-
# mypy: disable-error-code="arg-type"
import shutil
from pathlib import Path
from typing import Optional, Union, List

from .base_storage import BaseStorage, StorageType


class LocalStorage(BaseStorage):
    type: StorageType = StorageType.LOCAL

    def __init__(self, root: Optional[Union[str, Path]] = None):
        self.root = Path(root).expanduser().resolve() if root else None

    def get_size(self, filename: str) -> int:
        filename_path = self._normalize_path(filename)
        if not filename_path.exists():
            msg = f"File not found: {filename_path}"
            raise FileNotFoundError(msg)
        return filename_path.stat().st_size

    def save_file(self, filename: str, data: bytes) -> None:
        filename_path = self._normalize_path(filename)
        filename_path.parent.mkdir(parents=True, exist_ok=True)
        filename_path.write_bytes(data)

    def load_file(self, filename: str) -> bytes:
        filename_path = self._normalize_path(filename)
        if not filename_path.exists():
            msg = f"File not found: {filename_path}"
            raise FileNotFoundError(msg)
        return filename_path.read_bytes()

    def download_file(self, filename: str, target_filename: str) -> None:
        filename_path = self._normalize_path(filename)
        if not filename_path.exists():
            msg = f"File not found: {filename_path}"
            raise FileNotFoundError(msg)
        target_filename_path = self._normalize_path(target_filename)
        target_filename_path.write_bytes(filename_path.read_bytes())

    def copy_file(self, src: str, dst: str) -> None:
        """
        Copy a file or directory.

        Args:
            src: Source file or directory path.
            dst: Destination file or directory path.
        """
        src_path = self._normalize_path(src)
        dst_path = self._normalize_path(dst)

        if not src_path.exists():
            raise FileNotFoundError(f"Source path not found: {src_path}")

        if src_path == dst_path:
            return

        try:
            if src_path.is_dir():
                if dst_path.exists() and dst_path.is_dir():
                    shutil.rmtree(dst_path)
                shutil.copytree(
                    src_path,
                    dst_path,
                    symlinks=True,
                    dirs_exist_ok=True,
                )
            else:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)

        except Exception as e:
            raise IOError(
                f"Failed to copy {src_path} to {dst_path}: {str(e)}",
            ) from e

    def delete_file(self, filename: str) -> None:
        filename_path = self._normalize_path(filename)
        if not filename_path.exists():
            msg = f"File not found: {filename_path}"
            raise FileNotFoundError(msg)
        filename_path.unlink()

    def list_files(self, directory: str) -> List[str]:
        directory_path = self._normalize_path(directory)
        if not directory_path.exists():
            msg = f"Directory not found: {directory_path}"
            raise FileNotFoundError(msg)
        if not directory_path.is_dir():
            msg = f"{directory_path} is not a directory"
            raise NotADirectoryError(msg)
        return [
            str(p.relative_to(self.root)) for p in directory_path.iterdir()
        ]

    def exists(self, filename: str) -> bool:
        filename_path = self._normalize_path(filename)
        return filename_path.exists()

    def create_directory(self, directory: str) -> str:
        directory_path = self._normalize_path(directory)
        directory_path.mkdir(parents=True, exist_ok=True)
        return str(directory_path)

    def delete_directory(self, directory: str) -> None:
        directory_path = self._normalize_path(directory)
        if not directory_path.exists():
            msg = f"Directory not found: {directory_path}"
            raise FileNotFoundError(msg)
        if not directory_path.is_dir():
            msg = f"{directory_path} is not a directory"
            raise NotADirectoryError(msg)

        shutil.rmtree(directory_path)

    def _normalize_path(self, path: str) -> Path:
        path = Path(path).expanduser()
        if path.is_absolute():
            return path.resolve()
        if self.root is not None:
            return (self.root / path).resolve()

        return path.resolve()
