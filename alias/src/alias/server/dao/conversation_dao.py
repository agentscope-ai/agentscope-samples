# -*- coding: utf-8 -*-

from alias.server.dao.base_dao import BaseDAO
from alias.server.models.conversation import Conversation


class ConversationDao(BaseDAO[Conversation]):
    _model_class = Conversation
