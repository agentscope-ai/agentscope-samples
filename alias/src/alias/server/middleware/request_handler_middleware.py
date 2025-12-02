# -*- coding: utf-8 -*-
import time

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from alias.server.utils.request_handler import RequestHandler


class RequestHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ["OPTIONS"]:
            return await call_next(request)

        start_time = time.time()

        try:
            path_params = dict(request.path_params)
            body = await RequestHandler.get_request_body(request)
            query_params = dict(request.query_params)

            payload = self.format_log_message(
                request.method,
                body,
                path_params,
                query_params,
            )
            context = {
                "method": request.method,
                "path": request.url.path,
                "payload": payload,
            }

            logger.info("Request started.", context=context)

            response = await call_next(request)

            process_time = time.time() - start_time
            logger.info(
                f"Request finished in {process_time:.3f}s",
                context=context,
            )

            return response
        except Exception as e:
            logger.error(f"Request failed: {str(e)}", exc_info=True)
            raise

    def format_log_message(
        self,
        method: str,
        body: dict,
        path_params: dict,
        query_params: dict,
    ) -> dict:
        """Format the log message."""
        extra_parts = {}
        if path_params:
            extra_parts.update(path_params)
        if query_params and method == "GET":
            extra_parts.update(query_params)
        if body and method in ["POST", "PUT", "PATCH"]:
            sanitized_body = RequestHandler.sanitize_sensitive_data(body)
            extra_parts.update(sanitized_body)
        return extra_parts
