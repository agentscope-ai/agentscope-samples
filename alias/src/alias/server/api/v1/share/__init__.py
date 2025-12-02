# -*- coding: utf-8 -*-
from fastapi import APIRouter
from .conversation import router as conversation_router

router = APIRouter(prefix="/share")
router.include_router(conversation_router)
