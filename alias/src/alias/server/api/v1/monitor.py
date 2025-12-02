# -*- coding: utf-8 -*-
# pylint: disable=W0212 W0702
# mypy: disable-error-code="arg-type"
import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["monitor"])


@router.get("/health")
async def health() -> JSONResponse:
    """Health check."""
    content = {
        "pid": os.getpid(),
        "status": "ok",
    }
    return JSONResponse(
        content=content,
        status_code=200,
    )
