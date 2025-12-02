# -*- coding: utf-8 -*-
# pylint: disable=unused-import

# app is used by uvicorn when running: uvicorn main:app

from alias.memory_service.service.app.server import (  # noqa: E402, F401
    app,
)
