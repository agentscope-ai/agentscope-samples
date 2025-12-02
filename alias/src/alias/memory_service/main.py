# -*- coding: utf-8 -*-
import os

from alias.memory_service.service.app.main import app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("MEMORY_SERVICE_PORT", "8000")),
    )  # noqa: E501
