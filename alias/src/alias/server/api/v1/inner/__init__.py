# -*- coding: utf-8 -*-
from fastapi import APIRouter
from alias.server.api.deps import InnerAPIAuth
from .message import router as message_router
from .user import router as user_router
from .conversation import router as conversation_router

router = APIRouter(prefix="/inner", dependencies=[InnerAPIAuth])
router.include_router(message_router)
router.include_router(user_router)
router.include_router(conversation_router)
