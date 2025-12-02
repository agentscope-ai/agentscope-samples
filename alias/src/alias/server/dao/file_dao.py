# -*- coding: utf-8 -*-
from alias.server.dao.base_dao import BaseDAO
from alias.server.models.file import File


class FileDao(BaseDAO[File]):
    _model_class = File
