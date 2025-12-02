# -*- coding: utf-8 -*-
import uuid
from typing import List, Optional

from sqlmodel import SQLModel

from ..models.file import FileBase
from .response import ResponseBase


class FileInfo(FileBase):  # type: ignore[call-arg]
    id: uuid.UUID


class ShareFileRequest(SQLModel):
    share: Optional[bool] = True


class UploadFileResponse(ResponseBase):
    payload: FileInfo


class DeleteFilePayload(SQLModel):
    file_id: uuid.UUID


class DeleteFileResponse(ResponseBase):
    payload: DeleteFilePayload


class PageConversationFileInfo(SQLModel):
    total: int
    items: List[FileInfo]


class ListConversationsFileResponse(ResponseBase):
    payload: PageConversationFileInfo
