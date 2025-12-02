# -*- coding: utf-8 -*-
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from alias.server.utils.request_context import (
    RequestContext,
    request_context_var,
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_context = RequestContext.from_request(request)
        request_context_var.set(request_context)

        response = await call_next(request)
        return response
