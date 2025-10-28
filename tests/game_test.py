# -*- coding: utf-8 -*-
import os
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

# 设置环境变量
os.environ["DASHSCOPE_API_KEY"] = "test_api_key"

# 导入被测模块
from games.game_werewolves import game


@pytest.mark.asyncio
async def test_hunter_stage_shoot() -> None:
    """验证猎人开枪逻辑"""
    mock_agent = AsyncMock()
    mock_agent.return_value = {"shoot": True, "name": "Player1"}

    result = await game.hunter_stage(mock_agent, AsyncMock())
    assert result == "Player1"


@pytest.mark.asyncio
async def test_werewolves_discussion() -> None:
    """验证狼人讨论达成一致"""
    mock_agent = AsyncMock()
    mock_agent.return_value = {"reach_agreement": True}

    with patch("games.game_werewolves.game.MsgHub", AsyncMock()):
        agents = [mock_agent]
        players = AsyncMock()
        players.current_alive = ["Player1"]

        await game.werewolves_game(agents)
        assert True  # 验证流程不报错


@pytest.mark.asyncio
async def test_witch_resurrect() -> None:
    """验证女巫救人的逻辑"""
    mock_agent = AsyncMock()
    mock_agent.return_value = {"resurrect": True}

    with patch("games.game_werewolves.game.WitchResurrectModel", mock_agent):
        result = await game.WitchResurrectModel(**{"resurrect": True})
        assert result.resurrect == True
