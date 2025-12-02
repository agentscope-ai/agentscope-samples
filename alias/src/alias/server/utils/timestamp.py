# -*- coding: utf-8 -*-
from datetime import datetime, timezone


def get_current_time():
    return datetime.now(timezone.utc).isoformat()
