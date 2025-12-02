# -*- coding: utf-8 -*-

from alias.server.core.config import settings

from .base_storage import BaseStorage, StorageType


class StorageFactory:
    @classmethod
    def get_storage(cls, storage_type: StorageType = None) -> BaseStorage:
        if storage_type is None:
            storage_type = StorageType(settings.STORAGE_TYPE)

        if storage_type == StorageType.LOCAL:
            from alias.server.core.storage.local_storage import (
                LocalStorage,
            )

            return LocalStorage(settings.LOCAL_STORAGE_DIR)
        elif storage_type == StorageType.OSS:
            from alias.server.core.storage.oss_storage import (
                OSSStorage,
            )

            if (
                not settings.OSS_ACCESS_KEY_ID
                or not settings.OSS_ACCESS_KEY_SECRET
                or not settings.OSS_ENDPOINT
                or not settings.OSS_BUCKET_NAME
            ):
                raise ValueError(
                    "OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, "
                    "OSS_ENDPOINT, OSS_BUCKET_NAME are required",
                )

            return OSSStorage(
                access_key_id=settings.OSS_ACCESS_KEY_ID,
                access_key_secret=settings.OSS_ACCESS_KEY_SECRET,
                endpoint=settings.OSS_ENDPOINT,
                bucket_name=settings.OSS_BUCKET_NAME,
            )
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")
