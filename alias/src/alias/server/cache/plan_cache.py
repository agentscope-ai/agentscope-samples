# -*- coding: utf-8 -*-
from datetime import timedelta
from typing import Optional, Union

from alias.server.models.plan import Plan

from .base_cache import BaseCache


class PlanCache(BaseCache[Plan]):
    _model_cls = Plan
    _cache_prefix: Optional[str] = "plan"
    _cache_expire: Optional[Union[int, timedelta]] = 60
