# -*- coding: utf-8 -*-

from alias.server.dao.base_dao import BaseDAO
from alias.server.models.plan import Plan


class PlanDao(BaseDAO[Plan]):
    _model_class = Plan
