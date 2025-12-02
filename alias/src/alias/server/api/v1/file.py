# -*- coding: utf-8 -*-
import traceback
import uuid

from fastapi import APIRouter
from fastapi import File as FastAPIFile
from fastapi import HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from alias.server.api.deps import CurrentUser, SessionDep
from alias.server.schemas.file import (
    DeleteFilePayload,
    DeleteFileResponse,
    FileInfo,
    ShareFileRequest,
    UploadFileResponse,
)
from alias.server.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=UploadFileResponse)
async def upload_file(
    session: SessionDep,
    current_user: CurrentUser,
    file: UploadFile = FastAPIFile(...),
) -> UploadFileResponse:
    """Upload file."""
    file_service = FileService(session=session)
    file_info = await file_service.upload_file(current_user.id, file)
    return UploadFileResponse(
        status=True,
        message="Update file successfully.",
        payload=FileInfo.model_validate(file_info),
    )


@router.get("/{file_id}", response_model=UploadFileResponse)
async def get_file(
    session: SessionDep,
    _current_user: CurrentUser,
    file_id: uuid.UUID,
) -> UploadFileResponse:
    """Get file."""
    file_service = FileService(session=session)
    file = await file_service.get(file_id)

    return UploadFileResponse(
        status=True,
        message="Get file successfully.",
        payload=FileInfo.model_validate(file),
    )


@router.post("/{file_id}/share", response_model=UploadFileResponse)
async def share_file(
    session: SessionDep,
    current_user: CurrentUser,
    file_id: uuid.UUID,
    request: ShareFileRequest,
) -> UploadFileResponse:
    """Set file sharing."""
    file_service = FileService(session=session)
    file = await file_service.share_file(
        user_id=current_user.id,
        file_id=file_id,
        share=request.share,
    )

    return UploadFileResponse(
        status=True,
        message="Share file successfully.",
        payload=FileInfo.model_validate(file),
    )


@router.delete("/{file_id}", response_model=DeleteFileResponse)
async def delete_file(
    session: SessionDep,
    current_user: CurrentUser,
    file_id: uuid.UUID,
) -> DeleteFileResponse:
    """Delete file."""
    file_service = FileService(session=session)
    await file_service.delete_file(
        user_id=current_user.id,
        file_id=file_id,
    )

    return DeleteFileResponse(
        status=True,
        message="Delete file successfully.",
        payload=DeleteFilePayload(file_id=file_id),
    )


@router.get("/{file_id}/preview", response_class=StreamingResponse)
async def preview_file(
    session: SessionDep,
    current_user: CurrentUser,
    file_id: uuid.UUID,
) -> StreamingResponse:
    """Preview file (requires authentication)."""
    try:
        file_service = FileService(session=session)
        file_stream, media_type = await file_service.preview_file(
            file_id=file_id,
            user_id=current_user.id,
        )
        return StreamingResponse(file_stream, media_type=media_type)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Error previewing file: {str(e)}, "
                f"{traceback.format_exc()}"
            ),
        ) from e
