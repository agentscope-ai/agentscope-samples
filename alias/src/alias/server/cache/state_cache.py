# -*- coding: utf-8 -*-
from datetime import timedelta
from typing import Optional, Union

from alias.server.models.state import State

from .base_cache import BaseCache


class StateCache(BaseCache[State]):
    _model_cls = State
    _cache_prefix: Optional[str] = "state"
    _cache_expire: Optional[Union[int, timedelta]] = 60
