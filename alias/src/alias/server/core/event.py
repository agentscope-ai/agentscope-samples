# -*- coding: utf-8 -*-


from enum import Enum
from typing import Optional

from sqlmodel import SQLModel


class EventType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    FINISH = "finish"
    STOP = "stop"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class Event(SQLModel):
    event: EventType


class CreateEvent(Event):
    event: EventType = EventType.CREATE


class UpdateEvent(Event):
    event: EventType = EventType.UPDATE


class FinishEvent(Event):
    event: EventType = EventType.FINISH


class StopEvent(Event):
    event: EventType = EventType.STOP


class HeartBeatEvent(Event):
    event: EventType = EventType.HEARTBEAT


class ErrorEvent(Event):
    event: EventType = EventType.ERROR
    code: Optional[int] = 500
    message: Optional[str] = None
