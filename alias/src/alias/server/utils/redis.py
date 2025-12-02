# -*- coding: utf-8 -*-
from typing import Optional
from urllib.parse import quote_plus
import redis.asyncio as aioredis

from alias.server.core.config import settings


def get_redis_url(
    host: Optional[str] = None,
    port: Optional[int] = None,
    db: int = 0,
    password: Optional[str] = None,
    username: Optional[str] = None,
):
    host = host or settings.REDIS_HOST
    port = port or settings.REDIS_PORT
    db = db or settings.REDIS_DB
    password = password or settings.REDIS_PASSWORD
    username = username or settings.REDIS_USERNAME

    if host is None:
        raise ValueError("Host cannot be None")
    if port is None:
        raise ValueError("Port cannot be None")
    if not 0 <= db <= 15:
        raise ValueError("DB index must be between 0 and 15")

    redis_url = "redis://"
    if username and password:
        redis_url += f"{quote_plus(username)}:{quote_plus(password)}@"
    elif password:
        redis_url += f":{quote_plus(password)}@"
    redis_url += f"{host}:{port}/{db}"

    return redis_url


def init_aio_redis(
    host: Optional[str] = None,
    port: Optional[int] = None,
    db: int = 0,
    password: Optional[str] = None,
    username: Optional[str] = None,
):
    redis_url = get_redis_url(
        host=host,
        port=port,
        db=db,
        password=password,
        username=username,
    )
    client = aioredis.from_url(redis_url)
    return client


redis_client = init_aio_redis()
