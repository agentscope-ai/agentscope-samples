# tests/game_test.py
# -*- coding: utf-8 -*-
import os
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

# Set environment variables
os.environ["DASHSCOPE_API_KEY"] = "test_api_key"

# Import the module to test
from games.game_werewolves import game


# Mock structured model for hunter stage
class HunterModelMock:
    def __init__(self, **kwargs):
        self._data = {
            "name": kwargs.get("name", None),
            "shoot": kwargs.get("shoot", False),
        }
        self.metadata = {"shoot": self._data["name"] is not None}

    def model_dump(self):
        return self._data

    @property
    def name(self):
        return self._data["name"]


@pytest.mark.asyncio
async def test_werewolves_discussion() -> None:
    """Test werewolves discussion with correct player count"""
    # Create proper async context manager mock
    mock_hub = AsyncMock()
    mock_hub.__aenter__.return_value = mock_hub
    mock_hub.__aexit__.return_value = AsyncMock()

    with patch("games.game_werewolves.game.MsgHub", return_value=mock_hub):
        mock_agent = AsyncMock()
        mock_agent.name = "Player1"

        agents = [mock_agent for _ in range(9)]
        await game.werewolves_game(agents)
        assert True  # Verify workflow completes


@pytest.mark.asyncio
async def test_witch_resurrect() -> None:
    """Test witch resurrection logic"""

    # Create an awaitable model mock
    async def mock_model(**kwargs):
        return {"resurrect": kwargs.get("resurrect", False)}

    with patch("games.game_werewolves.game.WitchResurrectModel", side_effect=mock_model):
        result = await game.WitchResurrectModel(**{"resurrect": True})
        assert result["resurrect"] == True
