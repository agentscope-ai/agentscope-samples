# -*- coding: utf-8 -*-

from alias.server.core.event import (
    CreateEvent,
    FinishEvent,
    UpdateEvent,
)
from alias.server.models.message import Message
from alias.server.models.plan import Plan
from alias.server.models.state import State


class MessageEvent:
    pass


class MessageCreateEvent(CreateEvent, MessageEvent):
    message: Message


class MessageUpdateEvent(UpdateEvent, MessageEvent):
    message: Message


class MessageFinishEvent(FinishEvent, MessageEvent):
    message: Message


class PlanEvent:
    pass


class PlanCreateEvent(CreateEvent, PlanEvent):
    plan: Plan


class StateEvent:
    pass


class StateCreateEvent(CreateEvent, StateEvent):
    state: State
