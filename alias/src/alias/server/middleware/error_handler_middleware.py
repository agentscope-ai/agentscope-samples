# -*- coding: utf-8 -*-
from fastapi import Request
from fastapi.responses import JSONResponse
import sentry_sdk
from alias.server.exceptions.base import BaseError


async def base_exception_handler(
    request: Request,
    exc: BaseError,
):  # pylint: disable=unused-argument
    sentry_sdk.capture_exception(exc)

    return JSONResponse(
        status_code=exc.code,
        content={"detail": exc.message},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )
