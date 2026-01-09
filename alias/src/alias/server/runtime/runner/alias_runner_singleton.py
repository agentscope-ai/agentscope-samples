# -*- coding: utf-8 -*-
import asyncio
from typing import Optional
from alias.server.runtime.runner.alias_runner import AliasRunner

_lock = asyncio.Lock()
_runner: Optional[AliasRunner] = None


async def get_alias_runner() -> AliasRunner:
    global _runner
    if _runner is not None:
        return _runner
    async with _lock:
        if _runner is None:
            _runner = AliasRunner()
            await _runner.start()
    return _runner
