# -*- coding: utf-8 -*-
from alias.server.models.plan import Roadmap

from .response import ResponseBase


class GetRoadmapResponse(ResponseBase):
    payload: Roadmap
