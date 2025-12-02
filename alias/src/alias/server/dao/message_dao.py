# -*- coding: utf-8 -*-

from alias.server.dao.base_dao import BaseDAO
from alias.server.models.message import Message


class MessageDao(BaseDAO[Message]):
    _model_class = Message
