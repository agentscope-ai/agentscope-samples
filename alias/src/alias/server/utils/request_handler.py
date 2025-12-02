# -*- coding: utf-8 -*-
# pylint: disable=R1721
from fastapi import HTTPException, Request


class RequestHandler:
    @staticmethod
    async def get_request_body(request: Request) -> dict:
        """Get the request body content."""
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                content_type = request.headers.get("Content-Type", "").lower()

                if "application/json" in content_type:
                    return await request.json()
                elif "application/x-www-form-urlencoded" in content_type:
                    return {
                        key: value
                        for key, value in await request.form().items()
                    }  # Convert to dict
                elif "multipart/form-data" in content_type:
                    form_data = await request.form()
                    return {
                        key: value for key, value in form_data.items()
                    }  # Convert to dict
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="Unsupported content type",
                    )
            except Exception as e:
                # Raise an HTTP exception with status 500 if decoding fails
                raise HTTPException(status_code=500, detail=str(e)) from e
        return {}

    @staticmethod
    def sanitize_sensitive_data(data: dict) -> dict:
        """Sanitize sensitive data."""
        sensitive_fields = {
            field.lower()
            for field in [
                "password",
                "token",
                "secret",
                "authorization",
                "api_key",
                "client_secret",
                "access_token",
                "refresh_token",
                "session_token",
                "private_key",
                "secret_key",
            ]
        }
        sanitized = data.copy()

        def sanitize_dict(d: dict):
            for key, value in d.items():
                # Sanitize keys that contain sensitive fields
                if any(
                    sensitive in key.lower() for sensitive in sensitive_fields
                ):
                    d[key] = "******"  # Sanitize sensitive fields
                elif isinstance(value, dict):
                    sanitize_dict(
                        value,
                    )  # Recursively sanitize nested dictionaries
                elif isinstance(value, list):
                    # Sanitize any dictionaries within a list
                    for item in value:
                        if isinstance(item, dict):
                            sanitize_dict(item)

        sanitize_dict(sanitized)
        return sanitized
