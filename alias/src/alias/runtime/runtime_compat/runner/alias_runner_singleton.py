# -*- coding: utf-8 -*-
import asyncio
from typing import Optional
from alias.runtime.runtime_compat.runner.alias_runner import AliasRunner

_lock: Optional[asyncio.Lock] = None
_runner: Optional[AliasRunner] = None


async def get_alias_runner() -> AliasRunner:
    global _lock, _runner

    if _runner is not None:
        return _runner

    if _lock is None:
        _lock = asyncio.Lock()

    async with _lock:
        if _runner is not None:
            return _runner
        runner = AliasRunner()
        await runner.start()
        _runner = runner
        return _runner
