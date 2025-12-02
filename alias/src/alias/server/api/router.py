# -*- coding: utf-8 -*-
from fastapi import APIRouter

from alias.server.api.v1 import router
from alias.server.core.config import settings

api_router = APIRouter(prefix=settings.API_V1_STR)
api_router.include_router(router)
