# -*- coding: utf-8 -*-

from alias.server.dao.base_dao import BaseDAO
from alias.server.models.state import State


class StateDao(BaseDAO[State]):
    _model_class = State
