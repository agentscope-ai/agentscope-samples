# -*- coding: utf-8 -*-
from fastapi import APIRouter

from alias.server.api.v1.auth import router as auth_router
from alias.server.api.v1.conversation import (
    router as conversation_router,
)
from alias.server.api.v1.chat import router as chat_router
from alias.server.api.v1.file import router as file_router
from alias.server.api.v1.inner import router as inner_router
from alias.server.api.v1.share import router as share_router
from alias.server.api.v1.user import router as user_router
from alias.server.api.v1.monitor import router as monitor_router

router = APIRouter()
router.include_router(user_router)
router.include_router(auth_router)
router.include_router(conversation_router)
router.include_router(chat_router)
router.include_router(file_router)
router.include_router(inner_router)
router.include_router(share_router)
router.include_router(monitor_router)
